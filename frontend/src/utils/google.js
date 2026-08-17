// 구글 로그인 스크립트(GSI)는 필요한 순간에만 불러온다.
// 로그인 화면과 회원 탈퇴 화면이 함께 쓴다.
const GSI_SRC = 'https://accounts.google.com/gsi/client'

export function loadGoogleSdk () {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve()
    let script = document.querySelector(`script[src="${GSI_SRC}"]`)
    if (!script) {
      script = document.createElement('script')
      script.src = GSI_SRC
      script.async = true
      script.defer = true
      document.head.appendChild(script)
    }
    script.addEventListener('load', resolve, { once: true })
    script.addEventListener('error', reject, { once: true })
  })
}

/**
 * 지정한 자리에 구글 버튼을 그리고, 사용자가 인증하면 credential 을 넘겨준다.
 * clientId 가 없거나 스크립트를 못 불러오면 아무 것도 하지 않는다.
 */
export async function renderGoogleButton (el, clientId, onCredential, options = {}) {
  if (!clientId || !el) return false
  try {
    await loadGoogleSdk()
  } catch (e) {
    return false
  }
  window.google.accounts.id.initialize({
    client_id: clientId,
    callback: (response) => onCredential(response.credential)
  })
  window.google.accounts.id.renderButton(el, {
    theme: 'outline', size: 'large', width: 280, text: 'signin_with', locale: 'ko', ...options
  })
  return true
}
