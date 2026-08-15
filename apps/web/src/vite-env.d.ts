/// <reference types="vite/client" />

interface Window {
  $3Dmol?: {
    createViewer: (el: HTMLElement, opts: Record<string, unknown>) => {
      addModel: (data: string, fmt: string) => void;
      setStyle: (sel: object, style: object) => void;
      zoomTo: () => void;
      render: () => void;
      clear: () => void;
    };
  };
  initRDKitModule?: (opts?: { locateFile?: (f: string) => string }) => Promise<RDKitModule>;
}

interface RDKitModule {
  get_mol: (smiles: string) => {
    get_descriptors: () => string;
    get_svg: (w: number, h: number) => string;
    delete: () => void;
    is_valid: () => boolean;
  };
}
