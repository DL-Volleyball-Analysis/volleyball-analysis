import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import type { Court } from '../api/types'
import { ClockContext, createClock } from '../playback/clock'
import { CornerPicker } from './CornerPicker'
import { CourtShots } from './CourtShots'

afterEach(() => vi.restoreAllMocks())

/** A 1920 x 1080 video shown in a 960 x 540 box: one screen pixel is two video pixels. */
function picker(props: Partial<Parameters<typeof CornerPicker>[0]> = {}) {
  const clock = createClock()
  const video = document.createElement('video')
  Object.defineProperties(video, { videoWidth: { value: 1920 }, videoHeight: { value: 1080 } })
  clock.attach(video)
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue(
    { left: 0, top: 0, width: 960, height: 540, right: 960, bottom: 540, x: 0, y: 0, toJSON: () => ({}) } as DOMRect)
  const onSave = vi.fn(), onCancel = vi.fn()
  render(
    <ClockContext.Provider value={clock}>
      <CornerPicker saving={false} error={null} onSave={onSave} onCancel={onCancel} {...props} />
    </ClockContext.Provider>,
  )
  const surface = document.querySelector('.cursor-crosshair') as HTMLElement
  const click = (x: number, y: number) => fireEvent.pointerDown(surface, { clientX: x, clientY: y })
  return { onSave, onCancel, click }
}

const CORNERS: [number, number][] = [[300, 150], [660, 150], [850, 400], [110, 400]] // screen pixels

test('four corners in order give a court to save, in video pixels', async () => {
  const { onSave, click } = picker()
  expect(screen.getByText(/far left corner/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Save court' })).toBeDisabled()
  CORNERS.forEach(([x, y]) => click(x, y))
  expect(screen.getByText('Check the lines, then save.')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Save court' }))
  expect(onSave).toHaveBeenCalledWith([[600, 300], [1320, 300], [1700, 800], [220, 800]], 'corners')
})

test('crossed corners cannot be saved; undo moves the last one', async () => {
  const { onSave, click } = picker()
  ;[CORNERS[0], CORNERS[2], CORNERS[1], CORNERS[3]].forEach(([x, y]) => click(x, y))
  expect(screen.getByText(/do not form a court/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Save court' })).toBeDisabled()
  await userEvent.click(screen.getByRole('button', { name: 'Undo' }))
  expect(screen.getByText(/near left corner/)).toBeInTheDocument()
  expect(onSave).not.toHaveBeenCalled()
})

test('the near-half preset asks for the centre line and saves its preset', async () => {
  const { onSave, click } = picker()
  await userEvent.selectOptions(screen.getByRole('combobox'), 'near_half')
  expect(screen.getByText(/left end of the centre line/)).toBeInTheDocument()
  expect(screen.getByText(/where the net posts stand/)).toBeInTheDocument()
  ;[[180, 340], [800, 340], [890, 530], [95, 530]].forEach(([x, y]) => click(x, y))
  await userEvent.click(screen.getByRole('button', { name: 'Save court' }))
  expect(onSave).toHaveBeenCalledWith([[360, 680], [1600, 680], [1780, 1060], [190, 1060]], 'near_half')
})

test('keyboard: Escape cancels, clicks on the letterbox bars are ignored', () => {
  const { onCancel, click } = picker()
  click(-5, 100) // left of the video
  expect(screen.getByText(/1 of 4/)).toBeInTheDocument()
  fireEvent.keyDown(screen.getByLabelText('Court corners'), { key: 'Escape' })
  expect(onCancel).toHaveBeenCalledOnce()
})

test('a server error is shown', () => {
  picker({ error: 'these points do not give a plausible court' })
  expect(screen.getByText('these points do not give a plausible court')).toBeInTheDocument()
})

const court: Court = {
  status: 'done', fps: 25, message: null,
  shots: [
    { shot: 0, start_frame: 0, end_frame: 249, status: 'needs_review', model: 'gym', corrected: false, samples: [] },
    { shot: 1, start_frame: 250, end_frame: 499, status: 'ok', model: 'gym', corrected: true, samples: [] },
  ],
}

test('court per shot: status, set and clear', async () => {
  const onSet = vi.fn(), onClear = vi.fn()
  render(<CourtShots court={court} busy={false} onSet={onSet} onClear={onClear} />)
  expect(screen.getByText('Doubtful, not used')).toBeInTheDocument()
  expect(screen.getByText('Set by you')).toBeInTheDocument()
  const [first, second] = screen.getAllByRole('button', { name: 'Set corners' })
  await userEvent.click(first)
  expect(onSet).toHaveBeenCalledWith(court.shots[0])
  await userEvent.click(screen.getByRole('button', { name: 'Clear' }))
  expect(onClear).toHaveBeenCalledWith(court.shots[1])
  expect(second).toBeEnabled()
})

test('court per shot before the court stage, and while busy', () => {
  const { rerender } = render(<CourtShots court={undefined} busy={false} onSet={vi.fn()} onClear={vi.fn()} />)
  expect(screen.getByText(/once the court stage has run/)).toBeInTheDocument()
  rerender(<CourtShots court={court} busy onSet={vi.fn()} onClear={vi.fn()} />)
  screen.getAllByRole('button').forEach((b) => expect(b).toBeDisabled())
})
