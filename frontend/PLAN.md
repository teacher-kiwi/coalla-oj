# Vue 3 + Vite 프론트엔드 마이그레이션 계획서

본 문서는 구형 Vue 2 + Webpack 기반의 프론트엔드를 최신 Vue 3 + Vite 스택으로 전면 개편하기 위한 마이그레이션 로드맵입니다.

## 🚨 사용자 검토 필요 (User Review Required)

> [!WARNING]
> 본 마이그레이션은 기존 프론트엔드 아키텍처를 새로 짜는 수준의 작업입니다.
> OJ 페이지의 `iview` 코드와 Admin 페이지의 `element-ui` 코드를 모두 `element-plus` 기반으로 재작성해야 합니다. 기능 누락을 방지하기 위해 이 계획의 방향성을 확정해 주셔야 합니다.

## 🏛️ 현재 아키텍처 참고

이 프로젝트는 **MPA(Multi-Page App)** 구조로, 두 개의 독립된 엔트리 포인트를 가집니다:

| 페이지 | 엔트리 | UI 프레임워크 | 용도 |
|--------|--------|--------------|------|
| OJ | `src/pages/oj/index.js` | **iView** | 일반 사용자용 |
| Admin | `src/pages/admin/index.js` | **Element UI** | 관리자용 |

각각 별도의 라우터, 별도의 HTML 템플릿을 사용하며, Vite에서도 이 MPA 구조를 유지해야 합니다.

> [!NOTE]
> **Vite MPA 진입점 구조:** Webpack 시절에는 `html-webpack-plugin`이 엔트리를 자동 분리해 주었으나, Vite에서는 프로젝트 루트에 진입용 HTML 파일을 직접 배치하는 방식이 가장 안정적입니다. 기존 `src/pages/oj/index.html`과 `src/pages/admin/index.html` 템플릿을 **프로젝트 루트**로 이동하여 `index.html`(OJ용), `admin.html`(Admin용)로 구성합니다.

---

## 📦 패키지 변경 사항 (Old vs New)

기존 `package.json`에서 호환되지 않는 레거시 패키지들을 덜어내고, Vue 3 생태계에 맞는 모던 패키지로 전면 교체합니다.

### 1. 코어 및 빌드 환경
- [DELETE] `vue 2.x` ➡️ [NEW] **`vue 3.x`** (Composition API 사용)
- [DELETE] `webpack`, `babel` 일체 ➡️ [NEW] **`vite`**, `@vitejs/plugin-vue`
- [DELETE] `vue-template-compiler` (Vue 3에서는 `@vue/compiler-sfc`가 내장)

### 2. 뷰 필수 생태계 (Ecosystem)
- [DELETE] `vuex 3.x` ➡️ [NEW] **`pinia`** (Vue 공식 추천 상태 관리)
- [DELETE] `vue-router 3.x` ➡️ [NEW] **`vue-router 4.x`** (Vue 3 호환 문법)
- [DELETE] `vue-i18n 7.x` ➡️ [NEW] **`vue-i18n 9.x`** (Vue 3 전용)
- [DELETE] `vuex-router-sync` (Pinia에서는 불필요, `state.route` 참조 코드 제거)

### 3. UI 프레임워크 (가장 큰 변경)
- [DELETE] `iview` (OJ 페이지에서 사용 중) ➡️ `element-plus`로 통합
- [DELETE] `element-ui` (Admin 페이지에서 사용 중) ➡️ `element-plus`로 업그레이드
- [NEW] **`element-plus`** (오직 하나의 프레임워크로 통일)

### 4. 유틸리티 및 컴포넌트
- [DELETE] `moment.js` ➡️ [NEW] **`dayjs`** + `duration`, `relativeTime`, `utc` 플러그인 (moment와 유사하나 duration 등은 플러그인 로드 필요)
- [DELETE] `tar-simditor`, `tar-simditor-markdown` ➡️ [NEW] **`v-md-editor`** 또는 **`Quill`** (마크다운 기반 텍스트 에디터 최신화)
- [DELETE] `vue-codemirror-lite` ➡️ [NEW] **`vue-codemirror`** 또는 **`@codemirror/vue`** (Vue 3 호환 CodeMirror)
- [DELETE] `vue-echarts 2.x` + `echarts 3.x` ➡️ [NEW] **`vue-echarts 6.x`** + **`echarts 5.x`** (import 방식 및 tree-shaking 변경)
- [DELETE] `raven-js` (Sentry 구 SDK) ➡️ [NEW] **`@sentry/vue`** (Vue 3 전용 Sentry SDK)
- [DELETE] `font-awesome 4.x` ➡️ [NEW] **`@element-plus/icons-vue`** (Element Plus 아이콘으로 통합)
- [KEEP] `axios` (마운트 방식만 수정)
- [KEEP] `katex` (커스텀 디렉티브 `v-katex`로 재작성)
- [KEEP] `blockly` (마운트 방식만 수정)
- [KEEP] `highlight.js` (커스텀 디렉티브 `v-highlight`로 재작성)
- [KEEP] `papaparse` (프레임워크 무관, 그대로 사용)
- [CHECK] `vue-cropper` (Vue 3 호환 버전 확인 필요)
- [CHECK] `browser-detect` (삭제 또는 유지 결정 필요)

---

## 🏗️ 단계별 수정 순서 (Modification Order)

안전하게 마이그레이션하기 위해 기존 코드를 백업해둔 상태이므로, 현재 `frontend` 디렉토리에 **직접 덮어쓰기(Overwrite)** 하는 방식으로 진행합니다.

### [Phase 1] 빌드 환경 교체 및 프로젝트 초기화
1. 레거시 설정 파일 삭제: `build/`, `config/`, `.babelrc`, `.eslintrc.js` 등 webpack/babel 관련 파일 제거.
2. `vite.config.js` 생성:
   - **MPA 설정**: 프로젝트 루트에 `index.html`(OJ), `admin.html`(Admin) 배치 후, `build.rollupOptions.input`에 두 HTML을 명시.
   - **Alias 설정**: 기존 webpack alias (`@` → `src/`, `@oj` → `src/pages/oj/`, `@admin` → `src/pages/admin/`)를 `resolve.alias`에 등록.
   - **프록시 설정**: 기존 `config/index.js`의 `proxyTable` 설정을 `server.proxy`로 이전.
   - **LESS 지원**: `less` 패키지를 devDependencies에 포함.
3. `package.json`을 새로 덮어쓰고, 계획된 최신 패키지들 일괄 설치 (`npm install`).
4. **환경변수 전환**: `process.env.*` 참조를 `import.meta.env.*`로 일괄 변경. 환경변수에 `VITE_` 접두사 적용.

### [Phase 2] 코어 로직 및 유틸리티 이식
1. `axios` 인터셉터 및 에러 핸들링 로직 이식.
2. `moment()` → `dayjs()` 변환:
   - `dayjs/plugin/duration`, `dayjs/plugin/relativeTime`, `dayjs/plugin/utc` 플러그인 등록.
   - `moment.duration().humanize()` 등의 API 차이점을 반영하여 `src/utils/time.js` 재작성.
3. `vuex` → `pinia` 변환:
   - state, getters, mutations, actions 구조를 pinia store로 변환.
   - `vuex-router-sync` 제거 — `state.route` 참조를 `useRoute()` 컴포저블로 대체.
4. 다국어(`i18n`) 번역 파일(en, ko, zh-CN, zh-TW) 복사 및 `vue-i18n 9.x` 플러그인에 연결.
5. **Vue 3 Breaking Changes 대응**:
   - `Vue.filter()` → 일반 함수 또는 computed로 전환 (`src/utils/filters.js` 관련).
   - `Vue.prototype.$error/$success/$Message/$Loading` → `app.config.globalProperties` 또는 `provide/inject` 패턴으로 전환.
   - `highlight.js`, `katex`를 **커스텀 디렉티브**(`v-highlight`, `v-katex`)로 재작성. 글로벌 플러그인 대신 디렉티브 방식을 채택하여 컴포넌트 단위 재사용성을 높이고, 불필요한 전역 부작용을 제거.
6. `raven-js` → `@sentry/vue`로 교체 (`src/utils/sentry.js` 재작성).

### [Phase 3] 컴포넌트 리팩토링 및 이식
기존 `iview`(OJ) 및 `element-ui`(Admin) 기반 화면을 순차적으로 `element-plus` & `<script setup>` (Composition API) 방식으로 재작성합니다.

1. **Mixin → Composable 전환**:
   - `mixins/emitter.js`: `$children` / `$parent` 사용 — Vue 3에서 삭제됨. `provide/inject`로 대체.
   - `mixins/problem.js`: iView `Icon` render function 사용 — Element Plus 아이콘 + Vue 3 `h()` 시그니처로 재작성.
   - `mixins/form.js`: `$refs[formName].validate` — Element Plus 폼 검증 API에 맞게 수정.
2. **OJ 페이지** (iView → Element Plus, 작업량 큼):
   - Layout & Navigation: NavBar, VerticalMenu, Panel, Pagination 등.
   - Auth & Public: Login, Register, Home, ProblemList, Announcements.
   - Core Interactive: Problem(Blockly/CodeMirror 연동), SubmissionDetails.
   - Contest, Rank, Settings 등 나머지 뷰.
3. **Admin 페이지** (Element UI → Element Plus, 상대적으로 수월):
   - SideMenu, TopNav, Dashboard 등 레이아웃.
   - Problem/Contest/User CRUD 뷰.
   - Simditor → v-md-editor 또는 Quill 교체 (파일 업로드 기능 포함).
4. **vue-router 4.x 호환 수정**:
   - `scrollBehavior` 리턴값: `{x: 0, y: 0}` → `{left: 0, top: 0}`.
   - `new VueRouter()` → `createRouter()`, `mode: 'history'` → `createWebHistory()`.
   - 라우터 가드 내 `Vue.prototype.$Loading` 호출을 새 방식으로 전환.

### [Phase 4] 통합 테스트 및 빌드 검증
1. 변환이 끝난 컴포넌트들을 `vue-router`에 등록.
2. 백엔드(Django API)와 정상 통신하는지 테스트.
3. MPA 빌드 테스트: OJ와 Admin 각각 정상 빌드되는지 확인.
4. 배포 설정 확인: `deploy/Dockerfile`, `deploy/nginx.conf`가 새 빌드 출력 경로와 일치하는지 검증.

---

## 🗑️ 삭제 예정 마이너 플러그인 (통폐합)

- [DELETE] `vue-clipboard2` ➡️ 브라우저 내장 Web API(`navigator.clipboard`)로 대체.
- [DELETE] `vue-analytics` ➡️ 구 버전 GA(Google Analytics). 최신 GA4용 `vue-gtag` 교체 또는 스크립트로 대체.
- [DELETE] `screenfull` ➡️ 브라우저 네이티브 Fullscreen API로 커버 가능.
- [DELETE] `babel-polyfill` ➡️ Vite는 모던 브라우저 대상이므로 불필요.
- 기타 현대 브라우저에서 기본 지원하거나 최신 생태계에 불필요한 플러그인들은 작업하며 모두 삭제(Pruning) 처리합니다.

---

## ✅ 사전 협의 완료 사항

> [!IMPORTANT]
> 1. **작업 방식:** 백업을 완료한 상태이므로 기존 `frontend` 디렉토리에 덮어쓰기로 마이그레이션 진행합니다.
> 2. **플러그인 가지치기:** 파편화되어 사용성 떨어지는 마이너 패키지들 적극 통폐합/삭제.
> 3. **언어 스택:** JavaScript를 유지합니다. (TypeScript는 마이그레이션 완료 후 별도로 점진 도입 검토)
