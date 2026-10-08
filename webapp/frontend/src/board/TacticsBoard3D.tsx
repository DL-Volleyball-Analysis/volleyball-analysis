// Rotatable 3D court with the rally's flights. Loaded with a dynamic import when its view opens, so
// three.js never enters the main bundle.
import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { Flight } from '../api/types'
import { LENGTH, LINES, NET_X, WIDTH } from '../court/geometry'
import { useClock } from '../playback/clock'
import { NET_TOP_M, ballAt, flightLabel, heightShare } from './flightGeometry'

/** Court metres (x along the length, y across, z up) -> three.js (y up), court centre at the origin. */
const v3 = (x: number, y: number, z: number) => new THREE.Vector3(x - LENGTH / 2, z, y - WIDTH / 2)

function token(name: string): THREE.Color {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return new THREE.Color(value || '#888888')
}

export default function TacticsBoard3D({ flights }: { flights: readonly Flight[] }) {
  const host = useRef<HTMLDivElement>(null)
  const clock = useClock()
  const flightsRef = useRef(flights)
  useEffect(() => {
    flightsRef.current = flights
  })

  useEffect(() => {
    const el = host.current
    if (!el) return
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio || 1)
    el.appendChild(renderer.domElement)
    const scene = new THREE.Scene()
    scene.background = token('--window')
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 200)
    camera.position.copy(v3(-7, -6, 8)) // behind a corner, so the net is not seen edge-on
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.copy(v3(LENGTH / 2, WIDTH / 2, 1))
    controls.maxPolarAngle = Math.PI / 2 - 0.05 // stay above the floor
    controls.update()

    const disposables: { dispose: () => void }[] = [renderer, controls]
    const add = <T extends THREE.Object3D>(o: T) => {
      scene.add(o)
      return o
    }
    const mat = <M extends THREE.Material>(m: M) => {
      disposables.push(m)
      return m
    }
    const geo = <G extends THREE.BufferGeometry>(g: G) => {
      disposables.push(g)
      return g
    }

    // floor: free zone, court, lines
    const freeZone = add(new THREE.Mesh(geo(new THREE.PlaneGeometry(LENGTH + 5, WIDTH + 5)), mat(new THREE.MeshBasicMaterial({ color: token('--free-zone') }))))
    freeZone.rotation.x = -Math.PI / 2
    freeZone.position.y = -0.01
    const court = add(new THREE.Mesh(geo(new THREE.PlaneGeometry(LENGTH, WIDTH)), mat(new THREE.MeshBasicMaterial({ color: token('--court') }))))
    court.rotation.x = -Math.PI / 2
    const lineMat = mat(new THREE.LineBasicMaterial({ color: token('--court-line') }))
    for (const [x1, y1, x2, y2] of LINES) add(new THREE.Line(geo(new THREE.BufferGeometry().setFromPoints([v3(x1, y1, 0), v3(x2, y2, 0)])), lineMat))

    // net: posts and the 1 m band below the top
    const netMat = mat(new THREE.LineBasicMaterial({ color: token('--ink') }))
    for (const y of [-0.5, WIDTH + 0.5]) add(new THREE.Line(geo(new THREE.BufferGeometry().setFromPoints([v3(NET_X, y, 0), v3(NET_X, y, NET_TOP_M)])), netMat))
    const band = add(new THREE.Mesh(geo(new THREE.PlaneGeometry(WIDTH + 1, 1)), mat(new THREE.MeshBasicMaterial({ color: token('--ink-muted'), transparent: true, opacity: 0.4, side: THREE.DoubleSide }))))
    band.rotation.y = Math.PI / 2
    band.position.copy(v3(NET_X, WIDTH / 2, NET_TOP_M - 0.5))
    for (const z of [NET_TOP_M, NET_TOP_M - 1]) add(new THREE.Line(geo(new THREE.BufferGeometry().setFromPoints([v3(NET_X, -0.5, z), v3(NET_X, WIDTH + 0.5, z)])), netMat))

    // flights: colour by height (one hue), dashed when low quality
    const accent = token('--accent')
    const floor = token('--court')
    const flightGroup = add(new THREE.Group())
    let flightParts: { dispose: () => void }[] = [] // released before each redraw
    const own = <T extends { dispose: () => void }>(x: T) => {
      flightParts.push(x)
      return x
    }
    const clearFlights = () => {
      flightGroup.clear()
      flightParts.forEach((x) => x.dispose())
      flightParts = []
    }
    const drawFlights = () => {
      clearFlights()
      for (const f of flightsRef.current) {
        const pts = f.samples.map((s) => v3(s.x, s.y, s.z))
        const colours = f.samples.flatMap((s) => {
          const c = floor.clone().lerp(accent, heightShare(s.z) / 100)
          return [c.r, c.g, c.b]
        })
        const g = own(new THREE.BufferGeometry().setFromPoints(pts))
        g.setAttribute('color', new THREE.Float32BufferAttribute(colours, 3))
        const m = own(f.quality === 'low'
          ? new THREE.LineDashedMaterial({ vertexColors: true, dashSize: 0.3, gapSize: 0.2 })
          : new THREE.LineBasicMaterial({ vertexColors: true }))
        const line = new THREE.Line(g, m)
        if (f.quality === 'low') line.computeLineDistances()
        line.name = flightLabel(f, 0)
        flightGroup.add(line)
        if (f.landing) {
          const mark = new THREE.Mesh(own(new THREE.CircleGeometry(0.22, 24)), own(new THREE.MeshBasicMaterial({ color: token('--ink') })))
          mark.rotation.x = -Math.PI / 2
          mark.position.copy(v3(f.landing.x_m, f.landing.y_m, 0.01))
          flightGroup.add(mark)
        }
      }
    }
    drawFlights()
    let drawn = flightsRef.current

    const ball = add(new THREE.Mesh(geo(new THREE.SphereGeometry(0.13, 20, 14)), mat(new THREE.MeshBasicMaterial({ color: '#ffd23f' }))))
    const dropLine = add(new THREE.Line(geo(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()])), mat(new THREE.LineBasicMaterial({ color: token('--ink-muted') }))))

    const resize = () => {
      const w = el.clientWidth || 300
      const h = Math.round(w * 0.62)
      renderer.setSize(w, h)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    resize()
    const ro = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(resize)
    ro?.observe(el)

    let frame = 0
    const loop = () => {
      frame = requestAnimationFrame(loop)
      if (drawn !== flightsRef.current) {
        drawn = flightsRef.current
        drawFlights()
      }
      const p = ballAt(flightsRef.current, clock.exactTime())
      ball.visible = dropLine.visible = p !== null
      if (p) {
        ball.position.copy(v3(p.x, p.y, p.z))
        dropLine.geometry.setFromPoints([v3(p.x, p.y, p.z), v3(p.x, p.y, 0)])
      }
      renderer.render(scene, camera)
    }
    frame = requestAnimationFrame(loop)

    return () => {
      cancelAnimationFrame(frame)
      ro?.disconnect()
      clearFlights()
      disposables.forEach((d) => d.dispose())
      el.removeChild(renderer.domElement)
    }
  }, [clock])

  return (
    <div
      ref={host}
      className="w-full overflow-hidden rounded-md border border-line"
      role="img"
      aria-label={`3D court with ${flights.length} flights; drag to rotate, scroll to zoom`}
    />
  )
}
