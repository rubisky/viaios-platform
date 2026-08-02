// Type declaration for optional cesium dependency
declare module 'cesium' {
  export const Viewer: any;
  export const Cartesian3: any;
  export const Cartesian2: any;
  export const Color: any;
  export const Rectangle: any;
  export const VerticalOrigin: any;
  export const UrlTemplateImageryProvider: any;
  export function createWorldTerrainAsync(opts?: any): Promise<any>;
}
