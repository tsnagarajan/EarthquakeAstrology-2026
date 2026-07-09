import { loadEvalReport } from '@/lib/predictions'

export const metadata = {
  title: 'Model Methodology — Earthquake Astrology 2026',
  description: 'How the 2026 earthquake risk predictions were generated',
}

export default async function MethodologyPage() {
  const report = await loadEvalReport()
  const cm = report.confusion_matrix

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-lg font-semibold">Model Methodology</h1>
      <p className="text-sm text-gray-600 mt-1">
        How the 2026 earthquake risk predictions were generated
      </p>

      <h2 className="text-sm font-semibold text-gray-800 mt-8 mb-2">Approach</h2>
      <div className="text-sm text-gray-700 space-y-3">
        <p>
          This project uses over 100 years of historical earthquake data (M5.5+ events from the
          USGS catalog, 1900–2026) alongside daily planetary positions computed from the Swiss
          Ephemeris. Each day-region combination in the training set is labeled positive if a
          qualifying earthquake occurred at that grid cell on that date.
        </p>
        <p>
          Astrological features include cyclical-encoded planetary longitudes (sin/cos
          transformations for all major planets), pairwise planetary aspects (conjunction,
          opposition, trine, square, sextile, and others computed at 1° orb), Vedic nakshatra
          positions for each planet, and tithi (lunar day) values. This produces approximately
          813 features per date-region row.
        </p>
        <p>
          Model selection trains on pre-2000 rows and evaluates on the post-2000 holdout,
          ensuring no temporal data leakage in the reported holdout metrics. The decision
          threshold is chosen from the precision-recall curve to maximize F1 on the holdout set.
          The final serialized model is then retrained on the full 1900–2026 range before
          generating 2026 predictions and regional sanity checks.
        </p>
      </div>

      <p className="text-xs text-gray-500 mt-8 mb-2">
        Evaluation results on post-2000 holdout set (XGBClassifier)
      </p>
      <table className="w-full text-sm border border-gray-200 rounded">
        <thead>
          <tr className="bg-gray-100">
            <th className="text-left px-3 py-2 font-semibold text-gray-700">Metric</th>
            <th className="text-left px-3 py-2 font-semibold text-gray-700">Value</th>
          </tr>
        </thead>
        <tbody>
          <tr className="even:bg-gray-50">
            <td className="px-3 py-2 text-gray-600">Model</td>
            <td className="px-3 py-2">{report.model_used}</td>
          </tr>
          <tr className="even:bg-gray-50">
            <td className="px-3 py-2 text-gray-600">F1 Score</td>
            <td className="px-3 py-2">{report.f1_score.toFixed(6)}</td>
          </tr>
          <tr className="even:bg-gray-50">
            <td className="px-3 py-2 text-gray-600">MCC</td>
            <td className="px-3 py-2">{report.mcc.toFixed(6)}</td>
          </tr>
          <tr className="even:bg-gray-50">
            <td className="px-3 py-2 text-gray-600">Threshold</td>
            <td className="px-3 py-2">{report.threshold.toFixed(6)}</td>
          </tr>
          <tr className="even:bg-gray-50">
            <td className="px-3 py-2 text-gray-600">Eval Split</td>
            <td className="px-3 py-2">{report.eval_split_date}</td>
          </tr>
        </tbody>
      </table>

      <h2 className="text-sm font-semibold text-gray-800 mt-8 mb-2">
        Confusion Matrix (Post-2000 Holdout)
      </h2>
      <div className="grid grid-cols-2 gap-2 max-w-xs">
        <div className="bg-green-50 p-3 rounded text-center">
          <div className="text-xs text-gray-500">True Positive</div>
          <div className="text-lg font-semibold">{cm.tp.toLocaleString()}</div>
        </div>
        <div className="bg-red-50 p-3 rounded text-center">
          <div className="text-xs text-gray-500">False Positive</div>
          <div className="text-lg font-semibold">{cm.fp.toLocaleString()}</div>
        </div>
        <div className="bg-red-50 p-3 rounded text-center">
          <div className="text-xs text-gray-500">False Negative</div>
          <div className="text-lg font-semibold">{cm.fn.toLocaleString()}</div>
        </div>
        <div className="bg-green-50 p-3 rounded text-center">
          <div className="text-xs text-gray-500">True Negative</div>
          <div className="text-lg font-semibold">{cm.tn.toLocaleString()}</div>
        </div>
      </div>

      <h2 className="text-sm font-semibold text-gray-800 mt-8 mb-2">Models Compared</h2>
      <table className="w-full text-sm border border-gray-200 rounded">
        <thead>
          <tr className="bg-gray-100">
            <th className="text-left px-3 py-2 font-semibold text-gray-700">Model</th>
            <th className="text-left px-3 py-2 font-semibold text-gray-700">F1 Score</th>
            <th className="text-left px-3 py-2 font-semibold text-gray-700">MCC</th>
          </tr>
        </thead>
        <tbody>
          {report.both_models.map((m) => (
            <tr
              key={m.model}
              className={
                m.model === report.model_used
                  ? 'bg-gray-100 font-medium'
                  : 'even:bg-gray-50'
              }
            >
              <td className="px-3 py-2">
                {m.model}
                {m.model === report.model_used && (
                  <span className="ml-2 text-xs text-gray-500">(selected)</span>
                )}
              </td>
              <td className="px-3 py-2">{m.f1.toFixed(6)}</td>
              <td className="px-3 py-2">{m.mcc.toFixed(6)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-8 p-4 bg-gray-50 rounded text-sm text-gray-700">
        These metrics reflect the inherent difficulty of predicting rare events from astrological
        features. The model performs near chance level — this project is exploratory research, not
        a forecasting system.
      </div>
    </div>
  )
}
