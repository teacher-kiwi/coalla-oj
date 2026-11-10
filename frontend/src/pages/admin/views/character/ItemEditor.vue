<template>
  <div class="workshop view">
    <Panel :title="isEdit ? '아이템 고치기' : '아이템 만들기'">
      <template #header>
        <el-button size="small" @click="router.push({ name: 'avatar-item-list' })">목록으로</el-button>
      </template>
      <div v-loading="loading" class="workshop-body">
        <el-tabs v-model="tab">
          <!-- ① 그리기 -->
          <el-tab-pane label="그리기" name="draw">
            <div class="grid">
              <div class="col">
                <el-radio-group v-model="slot" size="small" class="slots">
                  <el-radio-button v-for="k in SLOT_KEYS" :key="k" :value="k"
                                   :disabled="isEdit && k !== slot">{{ SLOTS[k].label }}</el-radio-button>
                </el-radio-group>
                <div v-if="SLOTS[slot].variants.length" class="row">
                  <span class="muted">{{ variantTitle }}</span>
                  <el-radio-group v-model="variants[slot]" size="small">
                    <el-radio-button v-for="v in SLOTS[slot].variants" :key="v" :value="v">
                      {{ variantButton(v) }}
                    </el-radio-button>
                  </el-radio-group>
                </div>
                <div class="toolbar">
                  <div class="tools">
                    <el-button v-for="t in TOOLS" :key="t.key" size="small"
                               :type="tool === t.key ? 'primary' : ''" @click="setTool(t.key)">
                      {{ t.label }}<kbd>{{ t.kbd }}</kbd>
                    </el-button>
                  </div>
                  <div class="toggles">
                    <el-checkbox v-model="guide">맨몸 가이드</el-checkbox>
                    <el-checkbox v-model="mirror">좌우 대칭</el-checkbox>
                  </div>
                </div>
                <div v-if="tool === 'select'" class="selbar">
                  <span class="muted">드래그해서 범위를 고르고, 안쪽을 끌어서 옮겨요. 다른 부위로 옮겨 붙일 수도 있어요.</span>
                  <div class="row">
                    <el-button size="small" @click="selCopy">복사 <kbd>Ctrl C</kbd></el-button>
                    <el-button size="small" @click="selPaste">붙여넣기 <kbd>Ctrl V</kbd></el-button>
                    <el-button size="small" @click="selFlip">좌우 뒤집기</el-button>
                    <el-button size="small" @click="selDelete">지우기 <kbd>Del</kbd></el-button>
                    <el-button size="small" @click="selDone">확정 <kbd>Enter</kbd></el-button>
                  </div>
                </div>
                <div class="palette">
                  <button v-for="hex in DISPLAY_ORDER" :key="hex" type="button" class="sw"
                          :class="{ on: PAL[color] === hex }" :style="{ background: hex }"
                          :aria-label="hex" @click="pickColor(hex)" />
                </div>
                <div class="stage">
                  <canvas ref="ed" class="editor-canvas" @pointerdown="onDown" @pointermove="onMove"
                          @pointerup="onUp" @pointercancel="onUp" />
                  <span class="muted">{{ regionsText }}</span>
                </div>
                <p class="note">{{ noteText }}</p>
                <div class="row">
                  <el-button size="small" :disabled="!canUndo" @click="undo">되돌리기 <kbd>Ctrl Z</kbd></el-button>
                  <el-button size="small" :disabled="!canRedo" @click="redo">다시 실행 <kbd>Ctrl Shift Z</kbd></el-button>
                  <el-button size="small" @click="autoShade">자동 명암 넣기</el-button>
                  <el-button size="small" @click="clearAll">전부 지우기</el-button>
                  <span class="muted">외곽선은 자동으로 그려져요</span>
                </div>
              </div>

              <div class="col side">
                <div class="box">
                  <h3>미리보기</h3>
                  <div class="pv-box">
                    <canvas ref="pv" width="192" height="224" class="pv" />
                    <el-radio-group v-model="anim" size="small">
                      <el-radio-button value="idle">서기</el-radio-button>
                      <el-radio-button value="walk">걷기</el-radio-button>
                      <el-radio-button value="jump">점프</el-radio-button>
                    </el-radio-group>
                  </div>
                  <el-select v-model="companions" multiple collapse-tags collapse-tags-tooltip clearable
                             size="small" placeholder="같이 입혀 볼 아이템" class="companions">
                    <el-option-group v-for="g in companionGroups" :key="g.slot" :label="g.label">
                      <el-option v-for="it in g.items" :key="it.id" :label="it.name" :value="it.id" />
                    </el-option-group>
                  </el-select>
                  <p class="muted small">자동으로 만들어진 동작 8장</p>
                  <div class="strip">
                    <figure v-for="(f, i) in FRAMES" :key="i">
                      <canvas :ref="el => { stripRefs[i] = el }" width="64" height="64" />
                      <figcaption>{{ f.label }}</figcaption>
                    </figure>
                  </div>
                </div>
                <div class="box">
                  <h3>저장</h3>
                  <el-form label-position="top" size="small" @submit.prevent="save">
                    <el-form-item label="아이템 이름">
                      <el-input v-model="form.name" maxlength="30" placeholder="예) 노란 후드티" />
                    </el-form-item>
                    <el-form-item label="디자이너 (선택)">
                      <el-input v-model="form.designer" maxlength="30" placeholder="비워 두면 표시하지 않아요" />
                    </el-form-item>
                    <el-form-item label="가격 (코인)">
                      <el-input-number v-model="form.price" :min="0" :max="10000" :step="10" />
                    </el-form-item>
                    <el-form-item>
                      <el-switch v-model="form.visible" active-text="샵에 올리기" />
                    </el-form-item>
                    <el-button type="primary" native-type="submit" :loading="saving" class="full">
                      {{ isEdit ? '고친 내용 저장' : '아이템 저장' }}
                    </el-button>
                  </el-form>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- ② JSON -->
          <el-tab-pane label="JSON으로 만들기" name="json">
            <div class="grid">
              <div class="col">
                <div class="row">
                  <span class="muted">템플릿 종류</span>
                  <el-select v-model="jsonKind" size="small" class="json-kind">
                    <el-option v-for="o in JSON_KINDS" :key="o.value" :label="o.label" :value="o.value" />
                  </el-select>
                </div>
                <div class="row">
                  <el-button size="small" @click="jsonTemplate">빈 템플릿 넣기</el-button>
                  <el-button size="small" @click="jsonFromEditor">그리던 그림을 JSON으로</el-button>
                  <el-button size="small" @click="jsonExample">예시 넣기</el-button>
                  <el-button size="small" @click="copyPrompt">AI에게 부탁할 요청문 복사</el-button>
                </div>
                <el-input v-model="jsonText" type="textarea" :rows="22" class="code" spellcheck="false" />
                <div class="row">
                  <el-button type="primary" size="small" :disabled="!jsonItem" @click="jsonLoad">에디터로 불러오기</el-button>
                  <el-button size="small" @click="copyText(jsonText, 'JSON을 복사했어요')">JSON 복사</el-button>
                  <span class="muted">불러온 뒤 그리기 탭에서 다듬고 저장해요.</span>
                </div>
              </div>
              <div class="col side">
                <div class="box">
                  <h3>미리보기</h3>
                  <div class="pv-box"><canvas ref="jpv" width="192" height="224" class="pv" /></div>
                  <ul class="report">
                    <li v-for="(m, i) in jsonMsgs" :key="i" :class="m.t">{{ m.m }}</li>
                  </ul>
                </div>
              </div>
            </div>

            <div class="guide">
              <h3>JSON 작성요령</h3>
              <h4>1. 기본 구조</h4>
              <table class="tbl">
                <thead><tr><th>항목</th><th>필수</th><th>설명</th></tr></thead>
                <tbody>
                  <tr><td><code>slot</code></td><td>필수</td><td>아이템 종류. <code>hair</code> 헤어 · <code>hat</code> 모자·머리장식 · <code>face</code> 얼굴 · <code>acc</code> 안경·얼굴장식 · <code>top</code> 상의 · <code>bottom</code> 하의 · <code>shoes</code> 신발</td></tr>
                  <tr><td><code>colors</code></td><td>필수</td><td>글자 한 개와 색 코드를 짝지어요. 예: <code>"r": "#e43b44"</code></td></tr>
                  <tr><td><code>parts</code></td><td>필수</td><td>부위별 그림. 부위 이름 아래에 <code>x</code>, <code>y</code>, <code>rows</code>를 적어요.</td></tr>
                  <tr><td><code>cover</code></td><td>모자만</td><td><code>full</code> 머리카락 전부 숨기기 · <code>top</code> 윗머리만 숨기기 · <code>none</code> 장식만</td></tr>
                  <tr><td><code>btype</code></td><td>하의만</td><td><code>pants</code> 바지 · <code>skirt</code> 치마</td></tr>
                  <tr><td><code>kind</code></td><td>신발만</td><td><code>low</code> 단화·운동화 · <code>boots</code> 장화·부츠</td></tr>
                  <tr><td><code>mirror</code></td><td>선택</td><td><code>true</code>면 왼쪽만 그려도 오른쪽이 채워져요. 왼팔만 적으면 오른팔이, 몸통·머리·치마는 왼쪽 절반이 오른쪽으로 복사돼요.</td></tr>
                  <tr><td><code>name</code>, <code>designer</code></td><td>선택</td><td>아이템 이름과 디자이너</td></tr>
                  <tr><td><code>_</code>로 시작하는 항목</td><td>선택</td><td>메모용이라 읽을 때 무시해요.</td></tr>
                </tbody>
              </table>
              <h4>2. 그림 그리는 법</h4>
              <ul class="rules">
                <li><code>rows</code>의 글자 하나가 칸 하나예요. 왼쪽 위가 (0, 0)이고, 오른쪽으로 갈수록 x, 아래로 갈수록 y가 커져요.</li>
                <li><code>.</code>이나 공백은 빈칸이에요. <code>colors</code>에 없는 글자도 빈칸으로 처리하고 알려줘요.</li>
                <li><code>x</code>, <code>y</code>는 <code>rows</code> 첫 글자가 놓일 위치예요. 그림이 있는 부분만 적어도 돼요.</li>
                <li>외곽선은 자동으로 그려지니 적지 않아요. 명암은 같은 계열의 어두운 색으로 직접 넣어요.</li>
                <li>팔레트 64색에 없는 색은 가장 가까운 팔레트 색으로 바뀌어요.</li>
                <li>칠할 수 없는 곳(참고 그림의 <code>x</code>)과 템플릿 밖으로 넘친 칸은 지워지고, 몇 칸인지 알려줘요.</li>
              </ul>
              <h4>3. 부위와 크기</h4>
              <table class="tbl">
                <thead><tr><th>종류</th><th>부위 이름 (가로×세로)</th><th>그릴 수 있는 곳</th></tr></thead>
                <tbody>
                  <tr><td>헤어</td><td><code>head</code> 40×36</td><td>전체. y 0~15는 윗머리라 모자를 쓰면 숨겨질 수 있어요. 옆머리·묶은 머리는 y 16 아래에.</td></tr>
                  <tr><td>모자·머리장식</td><td><code>head</code> 40×36</td><td>전체. 윗머리만 숨기는 모자는 y 15줄까지 덮는 걸 추천해요.</td></tr>
                  <tr><td>얼굴</td><td><code>head</code> 40×36</td><td>x 8~31, y 17~32 네모 안</td></tr>
                  <tr><td>안경·얼굴장식</td><td><code>head</code> 40×36</td><td>전체. 눈은 x 13~15, 24~26 / y 22~25 근처예요.</td></tr>
                  <tr><td>상의</td><td><code>torso</code> 24×18 · <code>armL</code> 10×16 · <code>armR</code> 10×16</td><td>전체. 팔의 y 11~12는 손이에요.</td></tr>
                  <tr><td>하의 · 바지</td><td><code>legL</code> 11×16 · <code>legR</code> 11×16</td><td>y 0~10 (y 11부터는 신발 자리)</td></tr>
                  <tr><td>하의 · 치마</td><td><code>skirt</code> 26×16</td><td>전체. y 4 근처가 허리선이고 그 위는 상의에 가려져요.</td></tr>
                  <tr><td>신발 · 단화</td><td><code>legL</code> 11×16 · <code>legR</code> 11×16</td><td>y 11~15</td></tr>
                  <tr><td>신발 · 부츠</td><td><code>legL</code> 11×16 · <code>legR</code> 11×16</td><td>y 6~15</td></tr>
                </tbody>
              </table>
              <h4>4. 맨몸 참고 그림</h4>
              <p class="muted small">위에서 고른 템플릿 종류 기준이에요. o 외곽선 · s 피부 · c 기본 옷 · p 기본 반바지 · f 기본 신발 · h 기본 머리 · e 눈·입·볼 · x 그릴 수 없는 곳 · . 빈칸</p>
              <pre class="ref">{{ jsonRef }}</pre>
              <details>
                <summary>팔레트 64색 색상표</summary>
                <div class="palref">
                  <div v-for="hex in DISPLAY_ORDER" :key="hex"><i :style="{ background: hex }" />{{ hex }}</div>
                </div>
              </details>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </Panel>
  </div>
</template>

<script setup>
// 캐릭터 공방: 관리자가 샵에 올릴 아이템을 그린다. "우리반 도트 공방" 프로토타입의
// 그리기·JSON 탭을 옮겼다(선생님 검토·샵·놀이터 탭은 뺐다).
//
// 그림은 부위별 템플릿에 한 번만 그리면 걷기·점프 동작이 자동으로 만들어진다.
// 그림 배열은 크고 자주 바뀌어서 반응형으로 두지 않고, 바뀔 때마다 캔버스를 직접 다시 그린다.
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@admin/api'
import Panel from '@admin/components/Panel.vue'
import { PAL, PART, FRAMES, SLOTS, SLOT_KEYS, PAIR, FACE, ZONE, FOOT, BOOT, VARIANT_LABEL,
  composePixels, allowedCell, encodePart, itemFromRecord } from '@/utils/character'
import { DISPLAY_ORDER, blankDraft, cloneDraft, isBlank, partsToSave, shade, line, flood,
  guidePart, itemToJSON, templateJSON, parseItemJSON, refArt, aiPrompt, exampleItems } from '@/utils/workshop'
import { drawPixels, drawAnim } from '@/utils/characterCanvas'

const route = useRoute()
const router = useRouter()

const TOOLS = [
  { key: 'pen', label: '펜', kbd: 'P' }, { key: 'brush', label: '굵은 붓', kbd: 'B' },
  { key: 'line', label: '직선', kbd: 'L' }, { key: 'rect', label: '네모', kbd: 'R' },
  { key: 'fill', label: '채우기', kbd: 'F' }, { key: 'pick', label: '스포이드', kbd: 'I' },
  { key: 'eraser', label: '지우개', kbd: 'E' }, { key: 'select', label: '범위 선택', kbd: 'S' }
]

// 자리마다 편집 화면에 부위를 늘어놓는 자리(sheet)와 크기
const SHEETS = {
  head: { sheet: [{ p: 'head', x: 0, y: 0 }], w: 40, h: 36 },
  top: { sheet: [{ p: 'armL', x: 0, y: 1 }, { p: 'torso', x: 12, y: 0 }, { p: 'armR', x: 38, y: 1 }], w: 48, h: 18 },
  legs: { sheet: [{ p: 'legL', x: 0, y: 0 }, { p: 'legR', x: 13, y: 0 }], w: 24, h: 16 },
  skirt: { sheet: [{ p: 'skirt', x: 0, y: 0 }], w: 26, h: 16 }
}
const NOTES = {
  hair: '헤어를 입으면 기본 머리는 사라져요. 초록 점선 위쪽(윗머리)은 모자를 쓰면 숨겨질 수 있으니, 모자 밖으로 보일 옆머리·뒷머리·묶은 머리는 점선 아래에 그려주세요.',
  face: '눈·코·입을 그려요. 얼굴을 입으면 기본 얼굴은 사라져요. 걸을 때는 얼굴 전체가 진행 방향으로 1칸 움직여서 앞을 보는 것처럼 보여요.',
  acc: '안경, 마스크, 볼 스티커처럼 얼굴 위에 얹는 장식이에요. 헤어 위, 모자 아래에 그려져서 안경다리가 옆머리 위로 자연스럽게 걸쳐져요.',
  top: '몸통과 양팔을 한 번만 그리면 걷기·점프 8개 동작이 자동으로 만들어져요. 좌우 대칭을 켜두면 한쪽 팔만 그려도 반대쪽에 똑같이 그려져요.',
  'hat:full': '후드나 헬멧처럼 머리카락을 전부 감추는 모자예요. 얼굴 둘레까지 덮도록 그려주세요.',
  'hat:top': '비니·야구모자처럼 윗머리만 감춰요. 초록 점선까지 덮도록 그리면 어떤 헤어와 써도 머리가 모자 밖으로 삐져나오지 않아요.',
  'hat:none': '머리핀·리본처럼 헤어를 가리지 않는 장식이에요. 헤어 위에 그대로 얹혀요.',
  'bottom:pants': '바지·반바지를 그려요. 초록 점선 아래 발 구역은 신발 자리라서 칠할 수 없어요. 바짓단을 점선 바로 위까지 내리면 어떤 신발과도 자연스럽게 이어져요.',
  'bottom:skirt': '치마는 허리에 붙어서 몸통과 함께 움직이고, 다리는 치마 아래에서 따로 움직여요. 위쪽은 상의에 가려지니 허리선 조금 위부터 그려주세요.',
  'shoes:low': '단화·운동화는 초록 점선 아래 발 구역에만 그려요. 바지 위에 겹쳐 신겨져요.',
  'shoes:boots': '장화·부츠는 무릎 아래 점선까지 올라와도 돼요. 바지 위로 신겨져서 바지를 부츠 안에 넣은 모습이 돼요.'
}
const JSON_KINDS = SLOT_KEYS.flatMap(k => SLOTS[k].variants.length
  ? SLOTS[k].variants.map(v => ({ value: `${k}:${v}`, label: `${SLOTS[k].label} · ${VARIANT_LABEL[v]}` }))
  : [{ value: k, label: SLOTS[k].label }])

const isEdit = computed(() => !!route.params.itemId)
const loading = ref(false)
const saving = ref(false)
const tab = ref('draw')

/* ---------- 편집 상태 ---------- */
const slot = ref('top')
const variants = reactive({ hat: 'top', bottom: 'pants', shoes: 'low' })
const variant = computed(() => SLOTS[slot.value].variants.length ? variants[slot.value] : '')
const tool = ref('pen')
const color = ref(PAL.indexOf('#feae34'))
const guide = ref(true)
const mirror = ref(true)
const form = reactive({ name: '', designer: '', price: 50, visible: false })

const drafts = Object.fromEntries(SLOT_KEYS.map(k => [k, blankDraft(k)]))
const undoStacks = {}
const redoStacks = {}
const histVersion = ref(0)
const draft = () => drafts[slot.value]

const sheetOf = computed(() => {
  if (['hair', 'hat', 'face', 'acc'].includes(slot.value)) return SHEETS.head
  if (slot.value === 'top') return SHEETS.top
  if (slot.value === 'bottom' && variant.value === 'skirt') return SHEETS.skirt
  return SHEETS.legs
})
const regionsText = computed(() => {
  if (slot.value === 'hair') return '초록 점선 위 = 윗머리 · 아래 = 옆·뒷머리'
  if (slot.value === 'hat') return variant.value === 'top' ? '초록 점선 = 윗머리가 끝나는 선' : '머리'
  if (slot.value === 'face') return '점선 네모 안이 얼굴 자리예요'
  if (slot.value === 'acc') return '머리'
  if (slot.value === 'top') return '왼팔 · 몸통 · 오른팔'
  if (slot.value === 'bottom') return variant.value === 'skirt' ? '치마 · 흐린 그림은 허리와 다리 위치예요' : '왼다리 · 오른다리 (점선 아래는 신발 자리)'
  return '왼발 · 오른발'
})
const noteText = computed(() => NOTES[variant.value ? `${slot.value}:${variant.value}` : slot.value])
const variantTitle = computed(() => ({ hat: '이 모자를 쓰면 머리카락은', bottom: '하의 종류', shoes: '신발 종류' })[slot.value])
const variantButton = v => ({ top: '윗머리만 숨기기', full: '전부 숨기기', none: '그대로 두기 (장식)' })[v] || VARIANT_LABEL[v]

/* ---------- 되돌리기 ---------- */
const canUndo = computed(() => histVersion.value >= 0 && !!(undoStacks[slot.value] || []).length)
const canRedo = computed(() => histVersion.value >= 0 && !!(redoStacks[slot.value] || []).length)
function pushUndo () {
  const st = (undoStacks[slot.value] = undoStacks[slot.value] || [])
  st.push(cloneDraft(draft()))
  if (st.length > 40) st.shift()
  redoStacks[slot.value] = []
  histVersion.value++
}
function undo () {
  const st = undoStacks[slot.value]
  if (!st || !st.length) return
  ;(redoStacks[slot.value] = redoStacks[slot.value] || []).push(cloneDraft(effDraft()))
  float = null
  sel = null
  drafts[slot.value] = st.pop()
  histVersion.value++
  renderAll()
}
function redo () {
  const rs = redoStacks[slot.value]
  if (!rs || !rs.length) return
  commitFloat()
  sel = null
  ;(undoStacks[slot.value] = undoStacks[slot.value] || []).push(cloneDraft(draft()))
  drafts[slot.value] = rs.pop()
  histVersion.value++
  renderAll()
}

/* ---------- 도구 ---------- */
function setTool (t) {
  if (t !== 'select') { commitFloat(); sel = null }
  tool.value = t
  renderEditor()
}
function pickColor (hex) {
  color.value = PAL.indexOf(hex)
  if (tool.value === 'eraser' || tool.value === 'pick') setTool('pen')
}
function autoShade () {
  pushUndo()
  shade(draft())
  renderAll()
  ElMessage.success('아래·오른쪽 가장자리에 한 단계 어두운 색을 넣었어요')
}
function clearAll () {
  pushUndo()
  drafts[slot.value] = blankDraft(slot.value)
  renderAll()
}

const okPx = (p, x, y) => allowedCell(slot.value, variant.value, p, x, y)
function setPx (p, x, y, v) {
  const { w, h } = PART[p]
  if (x < 0 || y < 0 || x >= w || y >= h || !okPx(p, x, y)) return
  draft()[p][y * w + x] = v
}
function plot (p, x, y, v) {
  setPx(p, x, y, v)
  if (mirror.value) setPx(PAIR[p] || p, PART[p].w - 1 - x, y, v)
}
function stamp (p, x, y) {
  const v = tool.value === 'eraser' ? 0 : color.value + 1
  plot(p, x, y, v)
  if (tool.value === 'brush') { plot(p, x + 1, y, v); plot(p, x, y + 1, v); plot(p, x + 1, y + 1, v) }
}
function regionAt (sx, sy) {
  for (const r of sheetOf.value.sheet) {
    const { w, h } = PART[r.p]
    if (sx >= r.x && sx < r.x + w && sy >= r.y && sy < r.y + h) return r
  }
  return null
}

/* ---------- 캔버스 입력 ---------- */
const ed = ref(null)
let CS = 10
let drag = null
let selDrag = null
function cell (e) {
  const r = ed.value.getBoundingClientRect()
  const s = sheetOf.value
  return [Math.floor((e.clientX - r.left) / r.width * s.w), Math.floor((e.clientY - r.top) / r.height * s.h)]
}
function onDown (e) {
  if (tool.value === 'select') { selDown(e); return }
  const [sx, sy] = cell(e)
  const r = regionAt(sx, sy)
  if (!r) return
  e.preventDefault()
  ed.value.setPointerCapture(e.pointerId)
  const x = sx - r.x
  const y = sy - r.y
  const p = r.p
  const { w } = PART[p]
  if (tool.value === 'pick') {
    const v = draft()[p][y * w + x]
    if (v) color.value = v - 1
    setTool('pen')
    return
  }
  pushUndo()
  if (tool.value === 'fill') {
    const v = color.value + 1
    flood(draft()[p], p, x, y, v, (a, b) => okPx(p, a, b))
    if (mirror.value) {
      const q = PAIR[p] || p
      flood(draft()[q], q, w - 1 - x, y, v, (a, b) => okPx(q, a, b))
    }
    renderAll()
    return
  }
  drag = { r, x0: x, y0: y, lx: x, ly: y, snap: cloneDraft(draft()) }
  if (['pen', 'brush', 'eraser'].includes(tool.value)) stamp(p, x, y)
  renderEditor()
}
function onMove (e) {
  if (selDrag) { selMove(e); return }
  if (!drag) return
  const [sx, sy] = cell(e)
  const p = drag.r.p
  const x = sx - drag.r.x
  const y = sy - drag.r.y
  if (tool.value === 'line' || tool.value === 'rect') {
    drafts[slot.value] = cloneDraft(drag.snap)
    const v = color.value + 1
    if (tool.value === 'line') {
      line(drag.x0, drag.y0, x, y, (a, b) => plot(p, a, b, v))
    } else {
      const [a0, a1] = [Math.min(drag.x0, x), Math.max(drag.x0, x)]
      const [b0, b1] = [Math.min(drag.y0, y), Math.max(drag.y0, y)]
      for (let i = a0; i <= a1; i++) { plot(p, i, b0, v); plot(p, i, b1, v) }
      for (let j = b0; j <= b1; j++) { plot(p, a0, j, v); plot(p, a1, j, v) }
    }
  } else {
    line(drag.lx, drag.ly, x, y, (a, b) => stamp(p, a, b))
  }
  drag.lx = x
  drag.ly = y
  renderEditor()
}
function onUp () {
  if (selDrag) { selDrag = null; renderAll(); return }
  if (drag) { drag = null; renderSide() }
}

/* ---------- 범위 선택 · 이동 · 복사 ---------- */
let sel = null
let float = null
let clip = null
function getS (sx, sy) {
  const r = regionAt(sx, sy)
  if (!r) return 0
  return draft()[r.p][(sy - r.y) * PART[r.p].w + (sx - r.x)]
}
function setS (sx, sy, v, d = draft()) {
  const r = regionAt(sx, sy)
  if (!r || !okPx(r.p, sx - r.x, sy - r.y)) return
  d[r.p][(sy - r.y) * PART[r.p].w + (sx - r.x)] = v
}
function effDraft () {
  if (!float) return draft()
  const d = cloneDraft(draft())
  for (let j = 0; j < float.h; j++) {
    for (let i = 0; i < float.w; i++) {
      const v = float.px[j * float.w + i]
      if (v) setS(float.x + i, float.y + j, v, d)
    }
  }
  return d
}
function readRect (r) {
  const px = new Uint8Array(r.w * r.h)
  for (let j = 0; j < r.h; j++) for (let i = 0; i < r.w; i++) px[j * r.w + i] = getS(r.x + i, r.y + j)
  return px
}
function liftSel () {
  if (!sel || float) return
  pushUndo()
  float = { ...sel, px: readRect(sel) }
  for (let j = 0; j < sel.h; j++) for (let i = 0; i < sel.w; i++) setS(sel.x + i, sel.y + j, 0)
}
function commitFloat () {
  if (!float) return
  const f = float
  for (let j = 0; j < f.h; j++) {
    for (let i = 0; i < f.w; i++) {
      const v = f.px[j * f.w + i]
      if (v) setS(f.x + i, f.y + j, v)
    }
  }
  sel = { x: f.x, y: f.y, w: f.w, h: f.h }
  float = null
}
const inside = (r, x, y) => r && x >= r.x && y >= r.y && x < r.x + r.w && y < r.y + r.h
function clampCell (e) {
  const s = sheetOf.value
  const [x, y] = cell(e)
  return [Math.max(0, Math.min(s.w - 1, x)), Math.max(0, Math.min(s.h - 1, y))]
}
function selDown (e) {
  e.preventDefault()
  ed.value.setPointerCapture(e.pointerId)
  const [x, y] = clampCell(e)
  if (inside(float, x, y)) { selDrag = { mode: 'move', ox: x - float.x, oy: y - float.y }; return }
  if (inside(sel, x, y)) { liftSel(); selDrag = { mode: 'move', ox: x - float.x, oy: y - float.y }; return }
  commitFloat()
  sel = { x, y, w: 1, h: 1 }
  selDrag = { mode: 'make', x0: x, y0: y }
  renderAll()
}
function selMove (e) {
  if (selDrag.mode === 'move') {
    const [x, y] = cell(e)
    float.x = x - selDrag.ox
    float.y = y - selDrag.oy
  } else {
    const [x, y] = clampCell(e)
    sel = { x: Math.min(x, selDrag.x0), y: Math.min(y, selDrag.y0), w: Math.abs(x - selDrag.x0) + 1, h: Math.abs(y - selDrag.y0) + 1 }
  }
  renderEditor()
}
function selCopy () {
  const src = float || sel
  if (!src) { ElMessage.info('먼저 복사할 범위를 드래그해서 골라주세요'); return }
  clip = { x: src.x, y: src.y, w: src.w, h: src.h, px: float ? float.px.slice() : readRect(sel) }
  ElMessage.success('복사했어요. 붙여넣기로 꺼내서 원하는 곳에 끌어다 놓으세요')
}
function selPaste () {
  if (!clip) { ElMessage.info('복사한 범위가 없어요'); return }
  if (tool.value !== 'select') setTool('select')
  commitFloat()
  pushUndo()
  const s = sheetOf.value
  float = { x: Math.max(0, Math.min(clip.x + 2, s.w - clip.w)), y: Math.max(0, Math.min(clip.y + 2, s.h - clip.h)), w: clip.w, h: clip.h, px: clip.px.slice() }
  sel = null
  renderAll()
}
function selFlip () {
  if (!float && !sel) return
  liftSel()
  const f = float
  const n = new Uint8Array(f.px.length)
  for (let j = 0; j < f.h; j++) for (let i = 0; i < f.w; i++) n[j * f.w + i] = f.px[j * f.w + (f.w - 1 - i)]
  f.px = n
  renderAll()
}
function selDelete () {
  if (float) {
    float = null
    sel = null
  } else if (sel) {
    pushUndo()
    for (let j = 0; j < sel.h; j++) for (let i = 0; i < sel.w; i++) setS(sel.x + i, sel.y + j, 0)
    sel = null
  } else {
    return
  }
  renderAll()
}
function selDone () {
  commitFloat()
  sel = null
  renderAll()
}

/* ---------- 그리기 ---------- */
const GRID = 'rgba(23,33,43,.08)'
const REGION = '#2D5FC4'
const ACCENT = '#2C8655'
function renderEditor () {
  const canvas = ed.value
  if (!canvas) return
  const sl = sheetOf.value
  const ctx = canvas.getContext('2d')
  CS = Math.max(6, Math.floor(Math.min(560 / sl.w, 440 / sl.h)))
  if (canvas.width !== sl.w * CS || canvas.height !== sl.h * CS) {
    canvas.width = sl.w * CS
    canvas.height = sl.h * CS
    canvas.style.width = canvas.width + 'px'
  }
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  const d = draft()
  for (const r of sl.sheet) {
    const { w, h } = PART[r.p]
    const X = r.x * CS
    const Y = r.y * CS
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        ctx.fillStyle = (x + y) % 2 ? '#E9EEF2' : '#F7F9FB'
        ctx.fillRect(X + x * CS, Y + y * CS, CS, CS)
      }
    }
    if (guide.value) {
      ctx.globalAlpha = 0.4
      guidePart(slot.value, variant.value, r.p).forEach((c, i) => {
        if (c) { ctx.fillStyle = c; ctx.fillRect(X + (i % w) * CS, Y + Math.floor(i / w) * CS, CS, CS) }
      })
      ctx.globalAlpha = 1
    }
    d[r.p].forEach((v, i) => {
      if (v) { ctx.fillStyle = PAL[v - 1]; ctx.fillRect(X + (i % w) * CS, Y + Math.floor(i / w) * CS, CS, CS) }
    })
    ctx.strokeStyle = GRID
    ctx.lineWidth = 1
    ctx.beginPath()
    for (let i = 1; i < w; i++) { ctx.moveTo(X + i * CS + 0.5, Y); ctx.lineTo(X + i * CS + 0.5, Y + h * CS) }
    for (let j = 1; j < h; j++) { ctx.moveTo(X, Y + j * CS + 0.5); ctx.lineTo(X + w * CS, Y + j * CS + 0.5) }
    ctx.stroke()
    ctx.strokeStyle = REGION
    ctx.lineWidth = 2
    ctx.setLineDash([6, 4])
    ctx.strokeRect(X + 1, Y + 1, w * CS - 2, h * CS - 2)
    if (mirror.value && !PAIR[r.p]) {
      ctx.beginPath()
      ctx.moveTo(X + w * CS / 2, Y)
      ctx.lineTo(X + w * CS / 2, Y + h * CS)
      ctx.globalAlpha = 0.5
      ctx.stroke()
      ctx.globalAlpha = 1
    }
    ctx.setLineDash([])
    // 칠할 수 없는 곳은 흐리게 덮고 경계를 초록 점선으로
    const dash = () => { ctx.strokeStyle = ACCENT; ctx.lineWidth = 3; ctx.setLineDash([10, 6]) }
    if ((slot.value === 'bottom' && r.p !== 'skirt') || slot.value === 'shoes') {
      const ly = slot.value === 'shoes' && variant.value === 'boots' ? BOOT : FOOT
      ctx.fillStyle = '#ffffff'
      ctx.globalAlpha = 0.72
      if (slot.value === 'bottom') ctx.fillRect(X, Y + ly * CS, w * CS, (h - ly) * CS)
      else ctx.fillRect(X, Y, w * CS, ly * CS)
      ctx.globalAlpha = 1
      dash()
      ctx.beginPath(); ctx.moveTo(X, Y + ly * CS); ctx.lineTo(X + w * CS, Y + ly * CS); ctx.stroke()
      ctx.setLineDash([])
    }
    if (slot.value === 'face') {
      ctx.fillStyle = '#ffffff'
      ctx.globalAlpha = 0.72
      ctx.fillRect(X, Y, w * CS, FACE.y0 * CS)
      ctx.fillRect(X, Y + (FACE.y1 + 1) * CS, w * CS, (h - FACE.y1 - 1) * CS)
      ctx.fillRect(X, Y + FACE.y0 * CS, FACE.x0 * CS, (FACE.y1 - FACE.y0 + 1) * CS)
      ctx.fillRect(X + (FACE.x1 + 1) * CS, Y + FACE.y0 * CS, (w - FACE.x1 - 1) * CS, (FACE.y1 - FACE.y0 + 1) * CS)
      ctx.globalAlpha = 1
      dash()
      ctx.strokeRect(X + FACE.x0 * CS, Y + FACE.y0 * CS, (FACE.x1 - FACE.x0 + 1) * CS, (FACE.y1 - FACE.y0 + 1) * CS)
      ctx.setLineDash([])
    }
    if (r.p === 'head' && (slot.value === 'hair' || (slot.value === 'hat' && variant.value === 'top'))) {
      dash()
      ctx.beginPath(); ctx.moveTo(X, Y + ZONE * CS); ctx.lineTo(X + w * CS, Y + ZONE * CS); ctx.stroke()
      ctx.setLineDash([])
    }
  }
  drawSelection(ctx)
}
function drawSelection (ctx) {
  const r = float || sel
  if (!r) return
  if (float) {
    for (let j = 0; j < float.h; j++) {
      for (let i = 0; i < float.w; i++) {
        const v = float.px[j * float.w + i]
        if (v) { ctx.fillStyle = PAL[v - 1]; ctx.fillRect((float.x + i) * CS, (float.y + j) * CS, CS, CS) }
      }
    }
  }
  ctx.lineWidth = 2
  ctx.strokeStyle = '#ffffff'
  ctx.setLineDash([])
  ctx.strokeRect(r.x * CS + 1, r.y * CS + 1, r.w * CS - 2, r.h * CS - 2)
  ctx.strokeStyle = '#17212B'
  ctx.setLineDash([6, 6])
  ctx.strokeRect(r.x * CS + 1, r.y * CS + 1, r.w * CS - 2, r.h * CS - 2)
  ctx.setLineDash([])
}

/* ---------- 미리보기 ---------- */
const savedItems = ref([])
const companions = ref([])
const companionGroups = computed(() => SLOT_KEYS.filter(k => k !== slot.value).map(k => ({
  slot: k, label: SLOTS[k].label,
  items: savedItems.value.filter(r => r.slot === k && String(r.id) !== String(route.params.itemId))
})).filter(g => g.items.length))

function draftItem () {
  const item = { id: 'draft', slot: slot.value, parts: effDraft() }
  if (slot.value === 'hat') item.cover = variant.value
  if (slot.value === 'bottom') item.btype = variant.value
  if (slot.value === 'shoes') item.kind = variant.value
  return item
}
function previewEq () {
  const eq = {}
  for (const id of companions.value) {
    const r = savedItems.value.find(it => it.id === id)
    if (r && r.slot !== slot.value) eq[r.slot] = itemFromRecord(r)
  }
  const item = draftItem()
  if (!isBlank(partsToSave(slot.value, variant.value, item.parts))) eq[slot.value] = item
  return eq
}

const pv = ref(null)
const jpv = ref(null)
const anim = ref('walk')
const stripRefs = []
function renderSide () {
  const eq = previewEq()
  FRAMES.forEach((_, i) => {
    const c = stripRefs[i]
    if (!c) return
    const ctx = c.getContext('2d')
    ctx.clearRect(0, 0, 64, 64)
    drawPixels(ctx, composePixels({ frame: i, eq }), 64, 64)
  })
}
function renderAll () {
  renderEditor()
  renderSide()
}

let raf = 0
function loop (now) {
  const tick = Math.floor(now / 170)
  const cycle = ['idle', 'walk', 'jump'][Math.floor(now / 2400) % 3]
  if (tab.value === 'draw' && pv.value) drawAnim(pv.value, previewEq(), anim.value, tick)
  if (tab.value === 'json' && jpv.value) {
    if (jsonItem.value) {
      const it = jsonItem.value
      const eq = { [it.slot]: { id: 'json', slot: it.slot, parts: it.parts, cover: it.variant, btype: it.variant, kind: it.variant } }
      drawAnim(jpv.value, eq, cycle, tick)
    } else {
      jpv.value.getContext('2d').clearRect(0, 0, jpv.value.width, jpv.value.height)
    }
  }
  raf = requestAnimationFrame(loop)
}

/* ---------- 키보드 ---------- */
// 글자를 입력하는 칸에 있을 때만 단축키를 멈춘다. 종류 버튼(라디오)·체크박스를 누른 뒤에도
// 포커스가 그 input 에 남는데, 그때까지 막으면 단축키가 안 먹는 것처럼 보인다.
function isTyping (el) {
  if (!el) return false
  if (el.isContentEditable || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') return true
  return el.tagName === 'INPUT' && !['radio', 'checkbox', 'button', 'range'].includes(el.type)
}
function onKey (e) {
  if (tab.value !== 'draw') return
  if (isTyping(document.activeElement)) return
  const k = e.key.toLowerCase()
  const mod = e.ctrlKey || e.metaKey
  if (mod && k === 'z') { e.preventDefault(); if (e.shiftKey) redo(); else undo(); return }
  if (tool.value === 'select') {
    if (mod && k === 'c') { e.preventDefault(); selCopy(); return }
    if (mod && k === 'v') { e.preventDefault(); selPaste(); return }
    if (k === 'delete' || k === 'backspace') { e.preventDefault(); selDelete(); return }
    if (k === 'enter' || k === 'escape') { e.preventDefault(); selDone(); return }
    const nd = { arrowleft: [-1, 0], arrowright: [1, 0], arrowup: [0, -1], arrowdown: [0, 1] }[k]
    if (nd && (float || sel)) {
      e.preventDefault()
      if (!float) liftSel()
      float.x += nd[0]
      float.y += nd[1]
      renderAll()
      return
    }
  }
  if (mod) return
  const t = { p: 'pen', b: 'brush', l: 'line', r: 'rect', f: 'fill', i: 'pick', e: 'eraser', s: 'select' }[k]
  if (t) setTool(t)
}

/* ---------- JSON ---------- */
const jsonKind = ref('hat:top')
const jsonText = ref('')
const jsonItem = ref(null)
const jsonMsgs = ref([])
const jsonSel = () => { const [s, v] = jsonKind.value.split(':'); return [s, v || ''] }
const jsonRef = computed(() => { const [s, v] = jsonSel(); return refArt(s, v) })
let jsonTimer = 0
watch(jsonText, () => {
  clearTimeout(jsonTimer)
  jsonTimer = setTimeout(jsonCheck, 250)
})
function jsonCheck () {
  const { item, msgs } = parseItemJSON(jsonText.value)
  jsonItem.value = item
  jsonMsgs.value = msgs
}
function jsonTemplate () {
  const [s, v] = jsonSel()
  jsonText.value = templateJSON(s, v)
}
function jsonFromEditor () {
  const parts = partsToSave(slot.value, variant.value, effDraft())
  if (isBlank(parts)) { ElMessage.info('그리기 탭에 그린 그림이 없어요'); return }
  jsonText.value = itemToJSON({ name: form.name, designer: form.designer, slot: slot.value, variant: variant.value, parts })
  jsonKind.value = variant.value ? `${slot.value}:${variant.value}` : slot.value
}
function jsonExample () {
  const [s, v] = jsonSel()
  const ex = exampleItems().find(it => it.slot === s && it.variant === v)
  if (!ex) return
  jsonText.value = itemToJSON(ex)
  ElMessage.success(`예시 '${ex.name}'을(를) 넣었어요`)
}
function jsonLoad () {
  const it = jsonItem.value
  if (!it) return
  if (isEdit.value && it.slot !== slot.value) {
    ElMessage.error(`고치는 중인 아이템은 ${SLOTS[slot.value].label}이에요. 다른 종류는 새 아이템으로 만들어 주세요`)
    return
  }
  commitFloat()
  sel = null
  slot.value = it.slot
  if (it.variant) variants[it.slot] = it.variant
  pushUndo()
  drafts[it.slot] = { ...blankDraft(it.slot), ...cloneDraft(it.parts) }
  if (it.name) form.name = it.name
  if (it.designer) form.designer = it.designer
  tab.value = 'draw'
  nextTick(renderAll)
  ElMessage.success('에디터로 불러왔어요. 되돌리기로 이전 그림으로 돌아갈 수 있어요')
}
function copyText (text, label) {
  const fallback = () => ElMessage.warning('자동 복사가 막혀 있어요. 직접 선택해서 복사해 주세요')
  try {
    navigator.clipboard.writeText(text).then(() => ElMessage.success(label), fallback)
  } catch (e) {
    fallback()
  }
}
function copyPrompt () {
  const [s, v] = jsonSel()
  const label = JSON_KINDS.find(o => o.value === jsonKind.value).label
  copyText(aiPrompt(s, v, label), 'AI에게 보낼 요청문을 복사했어요. 아이템 설명만 바꿔서 붙여 넣으세요')
}

/* ---------- 저장 ---------- */
function save () {
  commitFloat()
  sel = null
  renderAll()
  const parts = partsToSave(slot.value, variant.value, draft())
  if (!form.name.trim()) { ElMessage.error('아이템 이름을 적어주세요'); return }
  if (isBlank(parts)) { ElMessage.error('아직 아무것도 그리지 않았어요'); return }
  const data = {
    name: form.name.trim(), designer: form.designer.trim(), price: form.price, visible: form.visible,
    slot: slot.value, variant: variant.value,
    parts: Object.fromEntries(Object.entries(parts).map(([p, a]) => [p, encodePart(a)]))
  }
  saving.value = true
  const req = isEdit.value
    ? api.updateAvatarItem({ ...data, id: Number(route.params.itemId) })
    : api.createAvatarItem(data)
  req.then(res => {
    if (!isEdit.value) router.replace({ name: 'edit-avatar-item', params: { itemId: res.data.data.id } })
  }, () => {}).finally(() => { saving.value = false })
}

function loadItem (id) {
  loading.value = true
  return api.getAvatarItem(id).then(res => {
    const r = res.data.data
    const it = itemFromRecord(r)
    slot.value = r.slot
    if (r.variant) variants[r.slot] = r.variant
    drafts[r.slot] = { ...blankDraft(r.slot), ...it.parts }
    undoStacks[r.slot] = []
    redoStacks[r.slot] = []
    Object.assign(form, { name: r.name, designer: r.designer, price: r.price, visible: r.visible })
  }, () => {}).finally(() => { loading.value = false })
}

watch([slot, variant, guide, mirror, sheetOf], () => {
  commitFloat()
  sel = null
  nextTick(renderAll)
})
watch(companions, renderSide)
watch(tab, t => { if (t === 'draw') nextTick(renderAll) })

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  api.getAvatarItems().then(res => { savedItems.value = res.data.data }, () => {})
  if (isEdit.value) await loadItem(route.params.itemId)
  else drafts.top = { ...blankDraft('top'), ...exampleItems().find(it => it.name === '노란 후드티').parts }
  jsonText.value = itemToJSON(exampleItems().find(it => it.name === '빨간 비니'))
  jsonCheck()
  nextTick(renderAll)
  raf = requestAnimationFrame(loop)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  cancelAnimationFrame(raf)
  clearTimeout(jsonTimer)
})
</script>

<style lang="less" scoped>
.workshop-body {
  padding: 0 4px;
}
.grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 20px;
  align-items: start;
}
@media (max-width: 1200px) {
  .grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
.col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.side {
  gap: 16px;
}
.box {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  h3 {
    margin: 0;
    font-size: 15px;
  }
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.muted {
  color: #909399;
  font-size: 13px;
}
.small {
  font-size: 12px;
  margin: 0;
}
kbd {
  font: inherit;
  font-size: 11px;
  opacity: .6;
  margin-left: 3px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: center;
  justify-content: space-between;
}
.tools {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  .el-button + .el-button {
    margin-left: 0;
  }
}
.toggles {
  display: flex;
  gap: 12px;
}
.selbar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #f5f7fa;
  border-radius: 6px;
  padding: 10px 12px;
}
.palette {
  display: grid;
  grid-template-columns: repeat(16, minmax(0, 1fr));
  gap: 4px;
  max-width: 560px;
}
.sw {
  aspect-ratio: 1;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, .18);
  padding: 0;
  cursor: pointer;
  &.on {
    outline: 3px solid #303133;
    outline-offset: 1px;
  }
}
.stage {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  overflow-x: auto;
}
.editor-canvas {
  max-width: 100%;
  height: auto;
  touch-action: none;
  cursor: crosshair;
  border-radius: 6px;
  image-rendering: pixelated;
}
.note {
  margin: 0;
  background: #f5f7fa;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 13px;
  color: #606266;
  max-width: 560px;
}
.pv-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
}
.pv {
  width: 192px;
  height: 224px;
  image-rendering: pixelated;
}
.companions {
  width: 100%;
}
.strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  figure {
    margin: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  canvas {
    width: 100%;
    max-width: 64px;
    aspect-ratio: 1;
    background: #f7f9fb;
    border: 1px solid #ebeef5;
    border-radius: 4px;
    image-rendering: pixelated;
  }
  figcaption {
    font-size: 11px;
    color: #909399;
  }
}
.full {
  width: 100%;
}
.json-kind {
  width: 220px;
}
.code :deep(textarea) {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.35;
  white-space: pre;
}
.report {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  li {
    padding: 6px 8px;
    border-radius: 4px;
    background: #f5f7fa;
    border-left: 3px solid #dcdfe6;
    &.ok { border-left-color: var(--el-color-success); }
    &.warn { border-left-color: var(--el-color-warning); }
    &.err { border-left-color: var(--el-color-danger); color: var(--el-color-danger); }
  }
}
.guide {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  h3, h4 {
    margin: 8px 0 0;
  }
}
.tbl {
  border-collapse: collapse;
  font-size: 13px;
  width: 100%;
  th, td {
    text-align: left;
    padding: 6px 10px;
    border-bottom: 1px solid #ebeef5;
    vertical-align: top;
  }
  th {
    color: #909399;
    font-weight: 600;
  }
}
code {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: .92em;
  background: #f5f7fa;
  padding: 1px 5px;
  border-radius: 4px;
}
.rules {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  line-height: 1.7;
}
pre.ref {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.2;
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
  margin: 0;
}
.palref {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
  gap: 6px;
  margin-top: 10px;
  div {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: 12px;
  }
  i {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid rgba(0, 0, 0, .18);
  }
}
</style>
