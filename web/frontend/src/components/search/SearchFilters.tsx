import React from 'react';
import { Row, Col, Select, Slider, DatePicker, InputNumber, Card, Typography } from 'antd';
import dayjs from 'dayjs';
import type { SearchFilters as SearchFiltersType } from '../../types/search';

const { RangePicker } = DatePicker;
const { Text } = Typography;

interface Props {
  filters: SearchFiltersType;
  onChange: (f: SearchFiltersType) => void;
  showCategory?: boolean;
  categoryOptions?: string[];
}

const TIME_PRESETS: { label: string; value: [dayjs.Dayjs, dayjs.Dayjs] }[] = [
  { label: '1h', value: [dayjs().subtract(1, 'hour'), dayjs()] },
  { label: '6h', value: [dayjs().subtract(6, 'hour'), dayjs()] },
  { label: '24h', value: [dayjs().subtract(24, 'hour'), dayjs()] },
  { label: '7d', value: [dayjs().subtract(7, 'day'), dayjs()] },
  { label: '30d', value: [dayjs().subtract(30, 'day'), dayjs()] },
  { label: '90d', value: [dayjs().subtract(90, 'day'), dayjs()] },
];

const SearchFilters: React.FC<Props> = ({ filters, onChange, showCategory = true, categoryOptions }) => {
  const update = (patch: Partial<SearchFiltersType>) => onChange({ ...filters, ...patch });

  return (
    <Card size="small" style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8, marginBottom: 16 }}>
      <Row gutter={[16, 12]} align="middle">
        {showCategory && (
          <Col xs={24} sm={12} md={6}>
            <Text style={{ color: '#a0a0a0', fontSize: 12, display: 'block', marginBottom: 4 }}>比对范围</Text>
            <Select
              value={filters.category}
              onChange={v => update({ category: v })}
              style={{ width: '100%' }}
              options={(categoryOptions || ['嫌疑人员', '涉案车辆', '全部']).map(k => ({ value: k, label: k }))}
            />
          </Col>
        )}

        <Col xs={24} sm={12} md={6}>
          <Text style={{ color: '#a0a0a0', fontSize: 12, display: 'block', marginBottom: 4 }}>时间范围</Text>
          <RangePicker
            showTime
            style={{ width: '100%' }}
            placeholder={['开始时间', '结束时间']}
            presets={TIME_PRESETS}
            value={
              filters.timeRange
                ? [dayjs(filters.timeRange[0]), dayjs(filters.timeRange[1])] as [dayjs.Dayjs, dayjs.Dayjs]
                : null
            }
            onChange={(dates) => {
              if (dates && dates[0] && dates[1]) {
                update({ timeRange: [dates[0].toISOString(), dates[1].toISOString()] });
              } else {
                update({ timeRange: null });
              }
            }}
          />
        </Col>

        <Col xs={12} sm={8} md={4}>
          <Text style={{ color: '#a0a0a0', fontSize: 12, display: 'block', marginBottom: 4 }}>
            相似度阈值: {filters.similarityThreshold.toFixed(2)}
          </Text>
          <Slider
            min={0.5} max={1.0} step={0.05}
            value={filters.similarityThreshold}
            onChange={v => update({ similarityThreshold: v as number })}
          />
        </Col>

        <Col xs={12} sm={8} md={3}>
          <Text style={{ color: '#a0a0a0', fontSize: 12, display: 'block', marginBottom: 4 }}>返回结果数</Text>
          <InputNumber
            min={5} max={200} step={5}
            value={filters.topK}
            onChange={v => update({ topK: v || 20 })}
            style={{ width: '100%' }}
          />
        </Col>
      </Row>
    </Card>
  );
};

export default SearchFilters;
