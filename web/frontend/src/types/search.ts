// ====== Library Target (from V2 API) ======
export interface LibraryTarget {
  目标ID: string;
  名称: string;
  类型?: string;
  类别?: string;
  属性?: Record<string, unknown>;
  标签?: string[];
  特征图片?: string[];
  最近出现?: string;
  关联案件?: string;
}

// ====== Search Mode ======
export type SearchMode = 'image' | 'text' | 'attribute' | 'composite';

// ====== Person Attributes ======
export interface PersonAttributes {
  gender: '男' | '女' | '';
  ageMin: number;
  ageMax: number;
  height: '矮' | '中' | '高' | '';
  topColor: string;
  bottomColor: string;
  hasBag: boolean;
  hasHat: boolean;
  hasGlasses: boolean;
  hasMask: boolean;
  accessories: string[];
}

// ====== Vehicle Attributes ======
export interface VehicleAttributes {
  vehicleType: '轿车' | 'SUV' | '面包车' | '卡车' | '';
  color: string;
  brand: string;
  model: string;
  plateNumber: string;
}

// ====== Search Filters (shared across all tabs) ======
export interface SearchFilters {
  cameraIds: string[];
  timeRange: [string, string] | null; // ISO strings
  similarityThreshold: number; // 0.5-1.0
  topK: number; // 10/20/50/100
  category: string; // 嫌疑人员 / 涉案车辆 / 全部
}

// ====== Search Result ======
export interface SearchResult {
  id: string;
  目标ID: string;
  名称: string;
  type: 'person' | 'vehicle' | 'face';
  category: string;
  imageUrl: string;
  thumbnailUrl: string;
  similarityScore: number; // 综合匹配度 0-100
  visualScore: number; // 视觉相似度 0-100
  attrScore: number; // 属性匹配度 0-100
  cameraId: string;
  cameraName: string;
  timestamp: string;
  attributes: Record<string, unknown>;
  tags: string[];
  matchDetail: string; // 匹配属性说明
  最近出现?: string;
  关联案件?: string;
}

// ====== Saved Search ======
export interface SavedSearch {
  id: string;
  name: string;
  mode: SearchMode;
  params: SearchParams;
  createdAt: string;
  alertOnNew?: boolean;
}

// ====== Search Params (serializable search state) ======
export interface SearchParams {
  mode: SearchMode;
  filters: SearchFilters;
  imageData?: string[]; // base64
  textQuery?: string;
  personAttrs?: PersonAttributes;
  vehicleAttrs?: VehicleAttributes;
  fusionStrategy?: 'early' | 'late' | 'cascade';
  weights?: { image: number; text: number; attr: number };
}

// ====== Default values ======
export const DEFAULT_PERSON_ATTRS: PersonAttributes = {
  gender: '', ageMin: 0, ageMax: 100, height: '',
  topColor: '', bottomColor: '', hasBag: false,
  hasHat: false, hasGlasses: false, hasMask: false, accessories: [],
};

export const DEFAULT_VEHICLE_ATTRS: VehicleAttributes = {
  vehicleType: '', color: '', brand: '', model: '', plateNumber: '',
};

export const DEFAULT_FILTERS: SearchFilters = {
  cameraIds: [], timeRange: null, similarityThreshold: 0.7,
  topK: 20, category: '嫌疑人员',
};
