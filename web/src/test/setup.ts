import '@testing-library/jest-dom';

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

class DOMMatrixReadOnlyStub {
  static fromFloat32Array() {
    return new DOMMatrixReadOnlyStub();
  }

  static fromFloat64Array() {
    return new DOMMatrixReadOnlyStub();
  }

  static fromMatrix() {
    return new DOMMatrixReadOnlyStub();
  }
}

if (!('ResizeObserver' in globalThis)) {
  (globalThis as { ResizeObserver?: unknown }).ResizeObserver = ResizeObserverStub;
}

if (!('DOMMatrixReadOnly' in globalThis)) {
  (globalThis as { DOMMatrixReadOnly?: unknown }).DOMMatrixReadOnly = DOMMatrixReadOnlyStub;
}

const svgElementPrototype = typeof SVGElement !== 'undefined' ? (SVGElement.prototype as { getBBox?: () => DOMRect }) : null;

if (svgElementPrototype && !svgElementPrototype.getBBox) {
  svgElementPrototype.getBBox = () =>
    ({
      x: 0,
      y: 0,
      width: 0,
      height: 0,
      top: 0,
      right: 0,
      bottom: 0,
      left: 0,
      toJSON: () => ({}),
    }) as DOMRect;
}
