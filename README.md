**Coalla OJ**

---

## 개발 환경

```bash
docker compose -f docker-compose.dev.yml up -d
```

프론트엔드는 http://localhost:8080, 백엔드 API 는 http://localhost:8000 이다.

## 검사

| 시점 | 검사 | 실행 위치 |
|---|---|---|
| 커밋 | 바뀐 파일의 flake8 · ESLint | 로컬 (pre-commit 훅) |
| 푸시 | flake8 · Django 테스트 · ESLint · 빌드 | 로컬 (pre-push 훅) |
| 푸시 후 / PR | 위 전부 | GitHub Actions |

훅은 클론한 뒤 한 번만 연결해주면 된다. `.git/hooks` 는 깃이 추적하지 않아
저장소의 `.githooks` 를 대신 보게 하는 방식이다.

```bash
git config core.hooksPath .githooks
```

훅은 컨테이너가 꺼져 있거나 `frontend/node_modules` 가 없으면 해당 검사를 건너뛴다
(pre-push 는 검사하지 못했다고 알리고 멈춘다). 급할 때는 `--no-verify` 로 넘길 수
있지만, 같은 검사를 CI 가 다시 하므로 결국 거기서 걸린다.

직접 돌리려면:

```bash
docker exec backend flake8 --statistics .
docker exec backend python manage.py test
cd frontend && npm run lint && npm run build
```
