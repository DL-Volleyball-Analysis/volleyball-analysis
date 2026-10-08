import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Vitest globals are off, so Testing Library cannot register its own cleanup.
afterEach(() => cleanup())

// jsdom has no layout: scrolling is a no-op in tests.
Element.prototype.scrollIntoView = function scrollIntoView() {}
