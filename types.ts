export enum TaskCategory {
  RESEARCH = '研發',
  ADMIN = '行政',
  PERSONAL = '個人',
  OTHER = '其他'
}

export interface Task {
  id: string;
  content: string;
  remindTime: string; // ISO string
  repeatDays: number[]; // 0-6 (Sunday-Saturday)
  category: TaskCategory;
  isActive: boolean;
  isCompleted: boolean;
  createdAt: number;
}

export interface AiSummaryResponse {
  summary: string;
  quote: string;
}

export const DAYS_OF_WEEK = [
  { value: 1, label: '週一' },
  { value: 2, label: '週二' },
  { value: 3, label: '週三' },
  { value: 4, label: '週四' },
  { value: 5, label: '週五' },
  { value: 6, label: '週六' },
  { value: 0, label: '週日' },
];