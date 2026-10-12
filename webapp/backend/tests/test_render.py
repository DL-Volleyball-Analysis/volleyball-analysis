import cv2
from test_api import run_worker_once, upload


def test_render_draws_every_frame_into_a_new_folder(client, clip, fake_ball, tmp_path):
    from vball_app import render
    v = upload(client, clip)
    assert run_worker_once()["status"] == "done"
    out = tmp_path / "not" / "yet" / "there.mp4"  # the folder does not exist
    assert render.render(v["id"], clip, out) == out and out.exists()
    cap = cv2.VideoCapture(str(out))
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 50 and int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == 320
    ok, frame = cap.read()
    assert ok and frame[:10].mean() < frame[60:120].mean()  # the status bar darkens the top of the frame
