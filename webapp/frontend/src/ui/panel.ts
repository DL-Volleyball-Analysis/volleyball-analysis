/** A tab panel is shown only while its tab is selected. */
export function panelClass(selected: boolean): string {
  return selected ? 'block' : 'hidden'
}
