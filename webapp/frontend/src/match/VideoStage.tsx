import { useEffect, useRef, type ReactNode } from 'react'
import { api } from '../api/client'
import type { Video } from '../api/types'
import { useClock } from '../playback/clock'
import { OverlayCanvas, type Layers } from './OverlayCanvas'

/** The match video with its overlay; registers the <video> element with the playback clock. `picker` (court
 *  corners) covers the video and takes the clicks while it is shown. */
export function VideoStage({ video, layers, picker }: { video: Video; layers: Layers; picker?: ReactNode }) {
  const clock = useClock()
  const el = useRef<HTMLVideoElement>(null)
  useEffect(() => (el.current ? clock.attach(el.current) : undefined), [clock])

  return (
    <div className="relative aspect-video w-full bg-black">
      <video ref={el} src={api.fileUrl(video.id)} controls playsInline preload="metadata" className="size-full object-contain" />
      <OverlayCanvas videoId={video.id} fps={video.fps ?? 30} layers={picker ? { ...layers, court: false } : layers} />
      {picker}
    </div>
  )
}
