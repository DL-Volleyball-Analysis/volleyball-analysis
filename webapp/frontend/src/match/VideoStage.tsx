import { useEffect, useRef } from 'react'
import { api } from '../api/client'
import type { Video } from '../api/types'
import { useClock } from '../playback/clock'
import { OverlayCanvas, type Layers } from './OverlayCanvas'

/** The match video with its overlay; registers the <video> element with the playback clock. */
export function VideoStage({ video, layers }: { video: Video; layers: Layers }) {
  const clock = useClock()
  const el = useRef<HTMLVideoElement>(null)
  useEffect(() => (el.current ? clock.attach(el.current) : undefined), [clock])

  return (
    <div className="relative aspect-video w-full bg-black">
      <video ref={el} src={api.fileUrl(video.id)} controls playsInline preload="metadata" className="size-full object-contain" />
      <OverlayCanvas videoId={video.id} fps={video.fps ?? 30} layers={layers} />
    </div>
  )
}
