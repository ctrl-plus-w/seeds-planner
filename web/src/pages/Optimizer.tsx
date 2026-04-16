import { useMutation, useQuery } from "@tanstack/react-query"
import { Sprout, Loader2 } from "lucide-react"
import { fetchPlants, postOptimize } from "@/api/client"
import type { OptimizeResponse, PlantQuantity } from "@/api/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { PlantPicker } from "@/components/PlantPicker"
import { PlotBuilder } from "@/components/PlotBuilder"
import { ResultsView } from "@/components/ResultsView"
import { useLocalStorage } from "@/hooks/useLocalStorage"

export function OptimizerPage() {
  const [selected, setSelected] = useLocalStorage<PlantQuantity[]>("seeds-planner:plants", [])
  const [plotAreas, setPlotAreas] = useLocalStorage<number[]>("seeds-planner:plots", [6, 8])
  const [popSize, setPopSize] = useLocalStorage<number>("seeds-planner:pop-size", 200)
  const [nGen, setNGen] = useLocalStorage<number>("seeds-planner:n-gen", 400)

  const plantsQuery = useQuery({
    queryKey: ["plants"],
    queryFn: fetchPlants,
    staleTime: 5 * 60 * 1000,
  })

  const optimize = useMutation<OptimizeResponse, Error>({
    mutationFn: () =>
      postOptimize({
        plants: selected,
        plot_areas: plotAreas,
        pop_size: popSize,
        n_gen: nGen,
      }),
  })

  const totalInstances = selected.reduce((s, p) => s + p.quantity, 0)
  const canRun =
    totalInstances >= 2 &&
    plotAreas.length >= 1 &&
    plotAreas.every((a) => a > 0) &&
    !optimize.isPending

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="border-b border-stone-200 bg-white">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <Sprout className="h-6 w-6 text-green-600" />
          <div>
            <h1 className="text-lg font-semibold text-stone-900">Seeds Planner</h1>
            <p className="text-xs text-stone-500">
              Optimisation NSGA-II du compagnonnage et de l'occupation des parcelles
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {plantsQuery.isLoading && (
          <Card>
            <CardContent>
              <div className="flex items-center gap-2 text-sm text-stone-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Chargement de la base de plantes…
              </div>
            </CardContent>
          </Card>
        )}

        {plantsQuery.isError && (
          <Card>
            <CardContent>
              <p className="text-sm text-red-600">
                Impossible de charger les plantes : {plantsQuery.error.message}
              </p>
              <p className="text-xs text-stone-500 mt-2">
                Vérifie que l'API tourne (<code>uv run uvicorn api.main:app</code>) et qu'un run de
                scraping existe dans <code>.out/</code>.
              </p>
            </CardContent>
          </Card>
        )}

        {plantsQuery.data && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Plantes</CardTitle>
                <CardDescription>
                  {plantsQuery.data.n_plants} disponibles · ordre = priorité
                </CardDescription>
              </CardHeader>
              <CardContent>
                <PlantPicker
                  plants={plantsQuery.data.plants}
                  selected={selected}
                  onChange={setSelected}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Parcelles</CardTitle>
                <CardDescription>Surface en mètres carrés</CardDescription>
              </CardHeader>
              <CardContent>
                <PlotBuilder plotAreas={plotAreas} onChange={setPlotAreas} />
              </CardContent>
            </Card>
          </div>
        )}

        {plantsQuery.data && (
          <Card>
            <CardHeader>
              <CardTitle>Paramètres</CardTitle>
              <CardDescription>Réglages de l'algorithme NSGA-II</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-6">
                <label className="flex items-center gap-3">
                  <span className="text-sm text-stone-700">Taille de population</span>
                  <Input
                    type="number"
                    min={10}
                    step={10}
                    value={popSize}
                    onChange={(e) => {
                      const n = parseInt(e.target.value, 10)
                      if (!isNaN(n) && n >= 10) setPopSize(n)
                    }}
                    className="w-24"
                  />
                </label>
                <label className="flex items-center gap-3">
                  <span className="text-sm text-stone-700">Générations</span>
                  <Input
                    type="number"
                    min={10}
                    step={10}
                    value={nGen}
                    onChange={(e) => {
                      const n = parseInt(e.target.value, 10)
                      if (!isNaN(n) && n >= 10) setNGen(n)
                    }}
                    className="w-24"
                  />
                </label>
              </div>
            </CardContent>
          </Card>
        )}

        {plantsQuery.data && (
          <div className="flex justify-end">
            <Button
              onClick={() => optimize.mutate()}
              disabled={!canRun}
              className="min-w-40"
            >
              {optimize.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Optimisation en cours…
                </>
              ) : (
                "Lancer NSGA-II"
              )}
            </Button>
          </div>
        )}

        {optimize.isError && (
          <Card>
            <CardContent>
              <p className="text-sm text-red-600">Erreur : {optimize.error.message}</p>
            </CardContent>
          </Card>
        )}

        {optimize.data && <ResultsView result={optimize.data} />}
      </main>
    </div>
  )
}
