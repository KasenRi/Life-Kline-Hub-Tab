import type { HttpOption } from '@/utils/request'
import { post } from '@/utils/request'

export function get<T>(options: Pick<HttpOption, 'silentAuth' | 'silentError'> = {}) {
  return post<T>({
    url: '/about',
    ...options,
  })
}
