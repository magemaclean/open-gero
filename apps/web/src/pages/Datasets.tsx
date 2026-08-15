import { useEffect, useState } from "react";
import { api } from "../api";
import { SkeletonCards, SkeletonTable } from "../components/Loading";
import { PageHeader, spotlightMove } from "../components/ui";
import type { Dataset, DatasetHit } from "../types";

export function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [compounds, setCompounds] = useState<DatasetHit[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api<Dataset[]>("/api/datasets")
      .then(async (ds) => {
        setDatasets(ds);
        if (ds[0]) setCompounds(await api<DatasetHit[]>(`/api/datasets/${ds[0].slug}/compounds`));
      })
      .finally(() => setLoading(false));
  }, []);
  return (
    <div>
      <PageHeader
        kicker="Reference sets"
        title="Longevity datasets"
        subtitle="Hand-curated public-literature snapshot used for similarity ranking."
      />
      {loading ? (
        <SkeletonCards count={2} />
      ) : (
        <div className="grid stagger" style={{ marginBottom: 16 }}>
          {datasets.map((d) => (
            <div key={d.id} className="card interactive" onMouseMove={spotlightMove}>
              <h2>{d.name}</h2>
              <p>{d.description}</p>
              <span className="badge">v{d.version}</span> <span className="badge">{d.license}</span>{" "}
              <span className="badge ok">{d.compound_count} compounds</span>
            </div>
          ))}
        </div>
      )}
      {loading ? (
        <SkeletonTable />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Organism</th>
                <th>Effect</th>
                <th>Citation</th>
              </tr>
            </thead>
            <tbody>
              {compounds.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>{c.organism}</td>
                  <td>
                    {c.effect_size}
                    <div className="muted">{c.effect_note}</div>
                  </td>
                  <td>
                    {c.citation}
                    {c.pmid && (
                      <div>
                        <a href={`https://pubmed.ncbi.nlm.nih.gov/${c.pmid}/`}>PMID {c.pmid}</a>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
