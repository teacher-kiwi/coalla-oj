// 마크다운 편집기의 그림 올리기.
//
// 편집기 컴포넌트는 관리자 화면과 교사 화면이 함께 쓴다. 각 앱의 api.js 가 전역
// axios 기본값을 세우는 구조라 어느 쪽을 불러야 할지 정할 수 없어서, 여기서는
// 경로를 그대로 두고 fetch 로 보낸다.
export async function uploadImage (file) {
  const form = new FormData()
  form.append('image', file)
  const resp = await fetch('/api/image', {
    method: 'POST',
    body: form,
    credentials: 'same-origin'
  })
  const body = await resp.json().catch(() => null)
  if (!body) throw new Error('그림을 올리지 못했습니다')
  // 서버는 {error, data} 로 답한다. 실패하면 data 에 사람이 읽을 문구가 온다.
  if (body.error) throw new Error(body.data)
  return body.data.url
}
