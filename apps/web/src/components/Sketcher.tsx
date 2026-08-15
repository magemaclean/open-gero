import { useEffect, useRef } from "react";

type Props = {
  smiles: string;
  onSmiles: (smiles: string) => void;
};

declare global {
  interface Window {
    JSApplet?: {
      JSME: new (id: string, w: string, h: string) => {
        smiles: () => string;
        readGenericMolecularInput: (s: string) => void;
        setCallBack: (name: string, fn: (ev: { action: string }) => void) => void;
      };
    };
    jsmeOnLoad?: () => void;
  }
}

let jsmeLoading: Promise<void> | null = null;

function loadJsme(): Promise<void> {
  if (window.JSApplet) return Promise.resolve();
  if (jsmeLoading) return jsmeLoading;
  jsmeLoading = new Promise((resolve, reject) => {
    const prev = window.jsmeOnLoad;
    window.jsmeOnLoad = () => {
      prev?.();
      resolve();
    };
    const script = document.createElement("script");
    script.src = "https://jsme-editor.github.io/dist/jsme/jsme.nocache.js";
    script.onerror = () => reject(new Error("JSME failed to load"));
    document.head.appendChild(script);
  });
  return jsmeLoading;
}

export function Sketcher({ smiles, onSmiles }: Props) {
  const id = useRef(`jsme-${Math.random().toString(36).slice(2)}`);
  const applet = useRef<{
    smiles: () => string;
    readGenericMolecularInput: (s: string) => void;
    setCallBack: (name: string, fn: (ev: { action: string }) => void) => void;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadJsme()
      .then(() => {
        if (cancelled || !window.JSApplet) return;
        const el = document.getElementById(id.current);
        if (!el) return;
        el.innerHTML = "";
        const inst = new window.JSApplet.JSME(id.current, "100%", "340px");
        applet.current = inst;
        inst.setCallBack("AfterStructureModified", () => {
          const s = inst.smiles();
          if (s) onSmiles(s);
        });
        if (smiles) inst.readGenericMolecularInput(smiles);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // Mount once; SMILES sync is handled below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const inst = applet.current;
    if (!inst) return;
    try {
      const current = inst.smiles();
      if (smiles && smiles !== current) inst.readGenericMolecularInput(smiles);
    } catch {
      /* applet not ready */
    }
  }, [smiles]);

  return (
    <div>
      <div id={id.current} className="sketcher" />
      <p className="muted" style={{ marginTop: 8, marginBottom: 0 }}>
        In-app sketcher (JSME). Draw a structure or paste SMILES below; they stay in sync.
      </p>
    </div>
  );
}
