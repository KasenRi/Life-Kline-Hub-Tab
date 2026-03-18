import { getExtensionStorageValue, setExtensionStorageValue, ss } from '@/utils/storage'
// import userDefaultAvatar from '@/assets/userDefaultAvatar.png'

const LOCAL_NAME = 'userStorage'

export interface UserInfo extends User.Info {
  // name: string
  // description: string
}

export interface UserState {
  userInfo: UserInfo
}

export function defaultSetting(): UserState {
  return {
    userInfo: {
      // headImage: userDefaultAvatar,
      name: '-- --',
    },
  }
}

export function getLocalState(): UserState {
  const localSetting: UserState | undefined = ss.get(LOCAL_NAME)
  return { ...defaultSetting(), ...localSetting }
}

export async function getStoredState(): Promise<UserState> {
  const localSetting: UserState | undefined = await getExtensionStorageValue<UserState>(LOCAL_NAME)
  return { ...defaultSetting(), ...localSetting }
}

export function setLocalState(setting: UserState): void {
  ss.set(LOCAL_NAME, setting)
  void setExtensionStorageValue(LOCAL_NAME, setting)
}
