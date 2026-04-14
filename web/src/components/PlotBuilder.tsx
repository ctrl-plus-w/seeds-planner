import { Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface PlotBuilderProps {
  plotAreas: number[]
  onChange: (areas: number[]) => void
}

export function PlotBuilder({ plotAreas, onChange }: PlotBuilderProps) {
  const update = (idx: number, value: string) => {
    const num = parseFloat(value)
    const next = [...plotAreas]
    next[idx] = isNaN(num) ? 0 : num
    onChange(next)
  }

  const add = () => onChange([...plotAreas, 6])

  const remove = (idx: number) => {
    onChange(plotAreas.filter((_, i) => i !== idx))
  }

  const total = plotAreas.reduce((s, a) => s + (a > 0 ? a : 0), 0)

  return (
    <div className="space-y-3">
      {plotAreas.length === 0 ? (
        <div className="text-sm text-stone-400 italic py-4 text-center border border-dashed border-stone-200 rounded-md">
          Aucune parcelle. Ajoutez-en au moins une.
        </div>
      ) : (
        <ul className="space-y-2">
          {plotAreas.map((area, idx) => (
            <li
              key={idx}
              className="flex items-center gap-3 rounded-md border border-stone-200 bg-stone-50 px-3 py-2"
            >
              <span className="text-xs text-stone-400 font-mono w-12">P{idx + 1}</span>
              <Input
                type="number"
                min="0"
                step="0.5"
                value={area}
                onChange={(e) => update(idx, e.target.value)}
                className="flex-1"
              />
              <span className="text-xs text-stone-500">m²</span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => remove(idx)}
                aria-label="Supprimer"
              >
                <X className="h-4 w-4" />
              </Button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-center justify-between">
        <Button type="button" variant="outline" size="sm" onClick={add}>
          <Plus className="h-4 w-4" />
          Ajouter une parcelle
        </Button>
        {plotAreas.length > 0 && (
          <span className="text-xs text-stone-500">Surface totale : {total.toFixed(1)} m²</span>
        )}
      </div>
    </div>
  )
}
