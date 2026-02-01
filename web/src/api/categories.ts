import apiClient from './client';
import type { CategoryListResponse } from '../types';

export async function fetchCategories(): Promise<CategoryListResponse> {
  const response = await apiClient.get<CategoryListResponse>('/categories');
  return response.data;
}
