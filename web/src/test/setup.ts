import '@testing-library/jest-dom';

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (!('ResizeObserver' in globalThis)) {
  (globalThis as typeof globalThis & { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
}

if (!('DOMMatrixReadOnly' in globalThis)) {
  (globalThis as typeof globalThis & { DOMMatrixReadOnly: typeof ResizeObserverStub }).DOMMatrixReadOnly =
    ResizeObserverStub;
}

if (typeof SVGElement !== 'undefined' && !SVGElement.prototype.getBBox) {
  SVGElement.prototype.getBBox = () => ({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
  });
}
