// 캐릭터 색 배열(utils/character.js)을 캔버스에 찍는다.
import { composePixels, ANIM, SIZE } from './character'

const scratch = typeof document !== 'undefined' ? document.createElement('canvas') : null

// px: 길이 w*h 색 배열. (x, y) 에 scale 배로 도트를 살려 그린다.
export function drawPixels (ctx, px, w, h, x = 0, y = 0, scale = 1, flip = false) {
  scratch.width = w
  scratch.height = h
  const sctx = scratch.getContext('2d')
  const img = sctx.createImageData(w, h)
  px.forEach((c, i) => {
    if (!c) return
    const k = i * 4
    img.data[k] = parseInt(c.slice(1, 3), 16)
    img.data[k + 1] = parseInt(c.slice(3, 5), 16)
    img.data[k + 2] = parseInt(c.slice(5, 7), 16)
    img.data[k + 3] = 255
  })
  sctx.putImageData(img, 0, 0)
  ctx.imageSmoothingEnabled = false
  if (flip) {
    ctx.save()
    ctx.translate(x + w * scale, y)
    ctx.scale(-1, 1)
    ctx.drawImage(scratch, 0, 0, w * scale, h * scale)
    ctx.restore()
  } else {
    ctx.drawImage(scratch, x, y, w * scale, h * scale)
  }
}

const JUMP_DY = [-5, -12, -12, -5]

// 동작 미리보기 한 장. tick 이 늘 때마다 다음 장을 그린다. 바닥 그림자도 함께.
export function drawAnim (canvas, eq, anim, tick, seed = '') {
  const ctx = canvas.getContext('2d')
  const s = Math.max(1, Math.floor(canvas.width / SIZE))
  const size = SIZE * s
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  let frame
  let dy = 0
  if (anim === 'jump') {
    const k = tick % 6
    frame = k < 2 ? 6 : k < 4 ? 7 : 0
    dy = k < 4 ? JUMP_DY[k] * s : 0
  } else {
    const q = ANIM[anim]
    frame = q[tick % q.length]
  }
  const x = Math.round((canvas.width - size) / 2)
  const y = canvas.height - size + dy
  ctx.fillStyle = '#dcdfe6'
  ctx.fillRect(x + 22 * s, canvas.height - 2 * s - 1, 20 * s, s)
  drawPixels(ctx, composePixels({ frame, eq, seed, look: anim === 'walk' ? 1 : 0 }), SIZE, SIZE, x, y, s)
}
