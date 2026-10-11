"""Fine-tune WASB's HRNet ball detector on broadcast and gym clips (change train-ball-detector).

Data: clip folders from scripts/build_ball_clips.py (512 x 288 letterboxed frames + labels in input pixels). A sample
is 3 consecutive frames (9 channels, RGB, ImageNet-normalised as vball.ball_detect.Wasb) and 3 Gaussian heatmaps
(sigma `--sigma` px; empty where there is no ball). Loss: the focal loss of CenterNet on the sigmoid heatmaps.
Augmentation: horizontal flip (labels mirrored) and brightness / contrast jitter. Sources are sampled with weights
(`--mix volleyball=0.5 orel=0.5`), so a small gym set is not drowned by broadcast clips. Model selection uses F1 on a
validation slice of the training clips (every `--val-every`-th clip per source), never the test matches.

WASB's model code is imported from a clone of github.com/nttcom/WASB-SBDT (MIT), `--wasb-src <clone>/src`; training
starts from its Volleyball-dataset weights (`--init`). Checkpoints (`last.pt`, `best.pt`) go to `--out` and a run
resumes from `last.pt`; the best model is exported to ONNX with the sigmoid included (`best.onnx`).

  python training/ball/train_wasb.py --clips <built dir> --wasb-src <clone>/src --init wasb_volleyball_best.pth.tar \
      --out runs/mixed --mix volleyball=0.5 orel=0.5 --epochs 8
"""
import argparse
import random
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

W, H, T = 512, 288, 3
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


def heatmap(x: float, y: float, sigma: float) -> np.ndarray:
    """H x W Gaussian with peak 1 at (x, y) in input pixels; zeros when x < 0 (no ball)."""
    if x < 0:
        return np.zeros((H, W), np.float32)
    xs, ys = np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32)[:, None]
    return np.exp(-((xs - x) ** 2 + (ys - y) ** 2) / (2 * sigma ** 2)).astype(np.float32)


def load_clips(root: Path, split: str) -> pd.DataFrame:
    m = pd.read_csv(root / "manifest.csv")
    m = m[(m["split"] == split) & (m["frames"] >= T)].copy()
    m["path"] = [str(root / f) for f in m["folder"]]
    return m.reset_index(drop=True)


def split_val(clips: pd.DataFrame, every: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Every `every`-th clip of each source (in manifest order) is held out for model selection."""
    k = clips.groupby("source").cumcount()
    return clips[k % every != 0].reset_index(drop=True), clips[k % every == 0].reset_index(drop=True)


class Windows:
    """3-frame windows of the given clips; `labels` cached per clip."""

    def __init__(self, clips: pd.DataFrame, sigma: float, augment: bool, stride: int = 1):
        self.sigma, self.augment = sigma, augment
        self.labels = {p: pd.read_csv(Path(p) / "labels.csv") for p in clips["path"]}
        self.items = [(p, s, i) for p, s in zip(clips["path"], clips["source"])
                      for i in range(0, len(self.labels[p]) - T + 1, stride)]

    def __len__(self):
        return len(self.items)

    def __getitem__(self, k: int):
        path, _, i = self.items[k]
        lab = self.labels[path].iloc[i:i + T]
        imgs = [cv2.cvtColor(cv2.imread(f"{path}/{f:05d}.jpg"), cv2.COLOR_BGR2RGB) for f in lab["frame"]]
        xy = lab[["x", "y"]].to_numpy(np.float32).copy()
        if self.augment and random.random() < 0.5:
            imgs = [im[:, ::-1] for im in imgs]
            xy[:, 0] = np.where(xy[:, 0] >= 0, (W - 1) - xy[:, 0], xy[:, 0])
        x = np.stack([im.astype(np.float32) / 255.0 for im in imgs])
        if self.augment:
            x = np.clip((x - 0.5) * random.uniform(0.8, 1.2) + 0.5 + random.uniform(-0.1, 0.1), 0, 1)
        x = ((x - MEAN) / STD).transpose(0, 3, 1, 2).reshape(T * 3, H, W)
        y = np.stack([heatmap(px, py, self.sigma) for px, py in xy])
        return np.ascontiguousarray(x, np.float32), y, xy


def source_weights(windows: Windows, mix: dict[str, float]) -> np.ndarray:
    """Per-window sampling weights so each source gets its share of `mix` (sources not in mix get none)."""
    src = np.array([s for _, s, _ in windows.items])
    w = np.zeros(len(src))
    for s, share in mix.items():
        n = (src == s).sum()
        if n:
            w[src == s] = share / n
    return w / w.sum()


def focal_loss(pred, target, alpha: float = 2.0, beta: float = 4.0):
    """CenterNet focal loss; pred are probabilities (after sigmoid), target Gaussian heatmaps."""
    import torch
    pred = pred.clamp(1e-4, 1 - 1e-4)
    pos = target.ge(0.99).float()
    pos_loss = -torch.log(pred) * (1 - pred) ** alpha * pos
    neg_loss = -torch.log(1 - pred) * pred ** alpha * (1 - target) ** beta * (1 - pos)
    return (pos_loss.sum() + neg_loss.sum()) / pos.sum().clamp(min=1.0)


def peaks(hm: np.ndarray, threshold: float = 0.5) -> tuple[float, float] | None:
    """The highest blob's centroid above threshold, or None."""
    mask = (hm >= threshold).astype(np.uint8)
    n, labels, _, cents = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 1:
        return None
    k = max(range(1, n), key=lambda j: hm[labels == j].max())
    return float(cents[k][0]), float(cents[k][1])


def f1_at(preds: list, truths: np.ndarray, tau: float) -> float:
    tp = fp = fn = 0
    for p, (gx, gy) in zip(preds, truths):
        visible = gx >= 0
        close = p is not None and visible and np.hypot(p[0] - gx, p[1] - gy) <= tau
        tp += close
        fp += p is not None and not close
        fn += visible and not close
    return 2 * tp / max(2 * tp + fp + fn, 1)


def build_model(wasb_src: str, init: str | None):
    import torch
    from omegaconf import OmegaConf
    sys.path.insert(0, wasb_src)
    from models import build_model as wasb_build  # WASB's code (MIT), cloned at run time
    net = wasb_build({"model": OmegaConf.load(Path(wasb_src) / "configs/model/wasb.yaml")})
    if init:
        net.load_state_dict(torch.load(init, map_location="cpu", weights_only=False)["model_state_dict"])
    return net


def with_sigmoid(net):
    """WASB's output (dict of scales -> logits) as 3 heatmaps in [0, 1]; also the ONNX export's graph."""
    import torch

    class Heatmaps(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, x):
            return self.m(x)[0].sigmoid()
    return Heatmaps(net)


def evaluate(model, windows: Windows, device, batch: int = 32, tau: float = 2.0) -> float:
    """F1 at `tau` input pixels (about 4-5 px at 720p-1080p) on the middle frame of each window."""
    import torch
    model.eval()
    preds, truths = [], []
    with torch.no_grad():
        for s in range(0, len(windows), batch):
            xs, _, xys = zip(*(windows[k] for k in range(s, min(s + batch, len(windows)))))
            hm = model(torch.from_numpy(np.stack(xs)).to(device)).float().cpu().numpy()
            preds += [peaks(h[1]) for h in hm]
            truths += [xy[1] for xy in xys]
    model.train()
    return f1_at(preds, np.array(truths), tau)


def train(args) -> float:
    import torch
    root = Path(args.clips)
    clips = load_clips(root, "train")
    mix = dict(kv.split("=") for kv in args.mix)
    mix = {k: float(v) for k, v in mix.items()}
    clips = clips[clips["source"].isin(mix)]
    tr, va = split_val(clips, args.val_every)
    train_w, val_w = Windows(tr, args.sigma, True), Windows(va, args.sigma, False, stride=T)
    print(f"train windows {len(train_w)} ({tr.groupby('source').size().to_dict()} clips), val windows {len(val_w)}")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    net = build_model(args.wasb_src, args.init)
    model = with_sigmoid(net).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    start, best = 0, -1.0
    if (out / "last.pt").exists():
        ck = torch.load(out / "last.pt", map_location="cpu", weights_only=False)
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        start, best = ck["epoch"] + 1, ck["best"]
        print("resumed at epoch", start)
    elif args.eval_init:
        best = evaluate(model, val_w, device)
        print(f"initial weights: val F1 {best:.3f}")
        torch.save({"model": model.state_dict()}, out / "best.pt")
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(args.epochs, 1), last_epoch=start - 1)
    weights = source_weights(train_w, mix)
    scaler = torch.amp.GradScaler(enabled=device.type == "cuda")
    for epoch in range(start, args.epochs):
        idx = np.random.choice(len(train_w), size=min(args.samples, len(train_w)), p=weights)
        loss_sum = 0.0
        for s in range(0, len(idx), args.batch):
            xs, ys, _ = zip(*(train_w[k] for k in idx[s:s + args.batch]))
            x, y = torch.from_numpy(np.stack(xs)).to(device), torch.from_numpy(np.stack(ys)).to(device)
            with torch.autocast(device.type, enabled=device.type == "cuda"):
                pred = model(x)
            loss = focal_loss(pred.float(), y)
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            loss_sum += float(loss) * len(xs)
        sched.step()
        f1 = evaluate(model, val_w, device)
        print(f"epoch {epoch}: loss {loss_sum / len(idx):.4f}, val F1 {f1:.3f}", flush=True)
        if f1 > best:
            best = f1
            torch.save({"model": model.state_dict()}, out / "best.pt")
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "epoch": epoch, "best": best}, out / "last.pt")
    model.load_state_dict(torch.load(out / "best.pt", map_location="cpu", weights_only=False)["model"])
    model.eval().cpu()
    torch.onnx.export(model, torch.randn(1, T * 3, H, W), out / "best.onnx", input_names=["frames"],
                      output_names=["heatmaps"], opset_version=17,
                      dynamic_axes={"frames": {0: "batch"}, "heatmaps": {0: "batch"}},
                      dynamo=False)  # TorchScript exporter: the default (dynamo) one needs onnxscript
    print("best val F1", round(best, 3), "->", out / "best.onnx")
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", required=True)
    ap.add_argument("--wasb-src", required=True)
    ap.add_argument("--init", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mix", nargs="+", default=["volleyball=0.5", "orel=0.5"])
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--samples", type=int, default=24000, help="windows drawn per epoch")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--sigma", type=float, default=2.5)
    ap.add_argument("--val-every", type=int, default=10)
    ap.add_argument("--eval-init", action="store_true", help="score the initial weights first (they become best.pt)")
    train(ap.parse_args())


if __name__ == "__main__":
    main()
