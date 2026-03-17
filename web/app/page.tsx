import { loadPredictions, groupPredictionsByDate } from '@/lib/predictions'
import { CalendarInteractive } from '@/components/CalendarInteractive'

// Hardcoded month definitions for March-December 2026
// (only 10 months, fixed range — hardcoded is clearer per RESEARCH.md)
const MONTHS = [
  { year: 2026, month: 2, label: 'March 2026' },
  { year: 2026, month: 3, label: 'April 2026' },
  { year: 2026, month: 4, label: 'May 2026' },
  { year: 2026, month: 5, label: 'June 2026' },
  { year: 2026, month: 6, label: 'July 2026' },
  { year: 2026, month: 7, label: 'August 2026' },
  { year: 2026, month: 8, label: 'September 2026' },
  { year: 2026, month: 9, label: 'October 2026' },
  { year: 2026, month: 10, label: 'November 2026' },
  { year: 2026, month: 11, label: 'December 2026' },
]

export default async function CalendarPage() {
  const predictions = await loadPredictions()
  const predictionsByDate = groupPredictionsByDate(predictions)

  return (
    <CalendarInteractive
      predictionsByDate={predictionsByDate}
      months={MONTHS}
    />
  )
}
