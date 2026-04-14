import { useMemo, useState } from "react"
import { Search, X, ArrowUp, ArrowDown } from "lucide-react"
import type { PlantQuantity, PlantSummary } from "@/api/types"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

interface PlantPickerProps {
  plants: PlantSummary[]
  selected: PlantQuantity[]
  onChange: (selected: PlantQuantity[]) => void
}

export function PlantPicker({ plants, selected, onChange }: PlantPickerProps) {
  const [query, setQuery] = useState("")

  const plantsBySlug = useMemo(() => {
    const map = new Map<string, PlantSummary>()
    for (const p of plants) map.set(p.slug, p)
    return map
  }, [plants])

  const selectedSlugs = useMemo(() => new Set(selected.map((s) => s.slug)), [selected])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return []
    return plants
      .filter(
        (p) =>
          !selectedSlugs.has(p.slug) &&
          (p.name.toLowerCase().includes(q) ||
            p.scientific_name.toLowerCase().includes(q) ||
            p.slug.includes(q)),
      )
      .slice(0, 12)
  }, [plants, query, selectedSlugs])

  const add = (slug: string) => {
    if (selectedSlugs.has(slug)) return
    onChange([...selected, { slug, quantity: 1 }])
    setQuery("")
  }

  const remove = (slug: string) => {
    onChange(selected.filter((s) => s.slug !== slug))
  }

  const updateQuantity = (slug: string, raw: string) => {
    const n = parseInt(raw, 10)
    const quantity = isNaN(n) || n < 1 ? 1 : Math.min(n, 200)
    onChange(selected.map((s) => (s.slug === slug ? { ...s, quantity } : s)))
  }

  const move = (slug: string, dir: -1 | 1) => {
    const idx = selected.findIndex((s) => s.slug === slug)
    const target = idx + dir
    if (idx < 0 || target < 0 || target >= selected.length) return
    const next = [...selected]
    ;[next[idx], next[target]] = [next[target], next[idx]]
    onChange(next)
  }

  const totalInstances = selected.reduce((s, p) => s + p.quantity, 0)

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-stone-400" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Rechercher une plante (tomato, basil, carrot...)"
          className="pl-9"
        />
        {filtered.length > 0 && (
          <div className="absolute left-0 right-0 top-full mt-1 max-h-64 overflow-auto rounded-md border border-stone-200 bg-white shadow-lg z-10">
            {filtered.map((p) => (
              <button
                key={p.slug}
                type="button"
                onClick={() => add(p.slug)}
                className="w-full text-left px-3 py-2 hover:bg-stone-100 text-sm flex items-center justify-between"
              >
                <span>
                  <span className="font-medium text-stone-900">{p.name}</span>
                  {p.scientific_name && (
                    <span className="text-stone-400 italic ml-2">{p.scientific_name}</span>
                  )}
                </span>
                <span className="text-xs text-stone-400">{p.area.toFixed(2)} m²</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {selected.length === 0 ? (
        <div className="text-sm text-stone-400 italic py-4 text-center border border-dashed border-stone-200 rounded-md">
          Aucune plante sélectionnée. La première a la priorité la plus haute.
        </div>
      ) : (
        <>
          <ol className="space-y-2">
            {selected.map((entry, idx) => {
              const p = plantsBySlug.get(entry.slug)
              if (!p) return null
              return (
                <li
                  key={entry.slug}
                  className="flex items-center gap-2 rounded-md border border-stone-200 bg-stone-50 px-3 py-2"
                >
                  <span className="text-xs text-stone-400 font-mono w-6">{idx + 1}.</span>
                  <span className="flex-1 text-sm min-w-0">
                    <span className="font-medium text-stone-900 truncate block">{p.name}</span>
                    <span className="text-stone-400 text-xs">{p.area.toFixed(2)} m² / unité</span>
                  </span>
                  <div className="flex items-center gap-1">
                    <Input
                      type="number"
                      min={1}
                      max={200}
                      value={entry.quantity}
                      onChange={(e) => updateQuantity(entry.slug, e.target.value)}
                      className="w-16 h-8 text-center text-sm"
                      aria-label={`Quantité pour ${p.name}`}
                    />
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => move(entry.slug, -1)}
                    disabled={idx === 0}
                    aria-label="Monter"
                  >
                    <ArrowUp className="h-4 w-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => move(entry.slug, 1)}
                    disabled={idx === selected.length - 1}
                    aria-label="Descendre"
                  >
                    <ArrowDown className="h-4 w-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => remove(entry.slug)}
                    aria-label="Retirer"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </li>
              )
            })}
          </ol>
          <div className="text-xs text-stone-500 text-right">
            {totalInstances} instance{totalInstances > 1 ? "s" : ""} à placer
          </div>
        </>
      )}
    </div>
  )
}
