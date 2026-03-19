declare global {
  interface Window {
    $loadingBar?: import('naive-ui').LoadingBarProviderInst
    $dialog?: import('naive-ui').DialogProviderInst
    $message?: import('naive-ui').MessageProviderInst
    $notification?: import('naive-ui').NotificationProviderInst
  }
}

declare module 'vue' {
  interface ComponentCustomProperties {
    $t: (key: string, params?: Record<string, any>) => string
  }
}

export {}
