import type { HttpOption } from '@/utils/request'
import { post } from '@/utils/request'

// export function getInfo<T>() {
//   return post<T>({
//     url: '/user/getInfo',
//   })
// }

export function getAuthInfo<T>(options: Pick<HttpOption, 'silentAuth' | 'silentError'> = {}) {
  return post<T>({
    url: '/user/getAuthInfo',
    ...options,
  })
}

export function getReferralCode<T>() {
  return post<T>({
    url: '/user/getReferralCode',
  })
}

export function updateInfo<T>(name: string) {
  return post<T>({
    url: '/user/updateInfo',
    data: { name },
  })
}

export function updatePassword<T>(oldPassword: string, newPassword: string) {
  return post<T>({
    url: '/user/updatePassword',
    data: { newPassword, oldPassword },
  })
}
