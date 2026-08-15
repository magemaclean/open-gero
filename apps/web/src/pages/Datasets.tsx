import { useEffect, useState } from "react";
import { api } from "../api";
import type { Dataset, DatasetHit } from "../types";

export function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [compounds, setCompounds] = useState<DatasetHit[]>([]);
  useEffect(() => {
    api<Dataset[]>("/api/datasets").then(async (ds) => {
      setDatasets(ds);
      if (ds[0]) setCompounds(await api<DatasetHit[]>(`/api/datasets/${ds[0].slug}/compounds`));
    });
  }, []);
  return (
    <div>
      <h1>Longevity datasets</h1>
      {datasets.map((d) => (
        <div key={d.id} className="card" style={{ marginBottom: 12 }}>
          <h2>{d.name}</h2>
          <p>{d.description}</p>
          <span className="badge">v{d.version}</span> <span className="badge">{d.license}</span>{" "}
          <span className="badge">{d.compound_count} compounds</span>
        </div>
      ))}
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
    </div>
  );
}
