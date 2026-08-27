# 상담일지 공유 페이지 (팀 전용)

농식품 유망기술 설명회 **수요기업 1:1 기술상담 일지**를 팀원이 함께 작성·공유하는 페이지입니다.
**지정된 팀원(이메일 허용목록)만 접근**할 수 있도록 실제 서버 인증(Supabase)으로 보호합니다.

- 로그인 → 상담일지 목록/검색 → 작성·수정·삭제 → CSV 내보내기
- 팀원이 추가/수정하면 **실시간으로** 다른 팀원 화면에 반영됩니다.
- 빌드 도구 없이 단일 `index.html` 로 동작하며 GitHub Pages 에 그대로 배포됩니다.

```
docs/consult/
├─ index.html            ← 공유 페이지 (이 파일 상단 CONFIG 를 수정)
├─ supabase-setup.sql    ← Supabase 에 한 번 실행하는 초기 설정 SQL
└─ README.md             ← 이 문서
```

---

## 왜 "비밀번호만 거는 정적 페이지"로는 안 되나요?

GitHub Pages 같은 정적 페이지에 자바스크립트 비밀번호를 넣으면, 브라우저에서 **소스 보기**만 해도
비밀번호와 데이터가 그대로 노출됩니다. 수요기업 상담 내용 같은 민감정보는 이 방식으로 보호되지 않습니다.

그래서 이 페이지는 **Supabase(무료 백엔드)** 를 사용합니다.
- 데이터는 **서버(DB)** 에 저장되어 페이지 소스로는 볼 수 없습니다.
- 로그인 사용자의 이메일이 **허용목록에 있을 때만** DB 보안정책(RLS)이 조회/작성을 허용합니다.
- 페이지에 넣는 `anon key` 는 **원래 공개되어도 되는 키**입니다. 보안은 열쇠를 숨기는 게 아니라 서버 정책이 담당합니다.

---

## 설정 순서 (최초 1회, 약 10분)

### 1. Supabase 프로젝트 만들기
1. https://supabase.com 접속 → **Start your project** → GitHub/이메일로 가입(무료)
2. **New project** 클릭 → 이름(예: `koat-consult`), 데이터베이스 비밀번호 지정, Region 은 `Northeast Asia (Seoul)` 권장
3. 프로젝트 생성까지 1~2분 대기

### 2. 데이터베이스 초기화 (SQL 실행)
1. 좌측 메뉴 **SQL Editor** → **New query**
2. 같은 폴더의 **`supabase-setup.sql`** 내용을 전체 복사해 붙여넣기
3. 파일 안의 **허용 팀원 이메일**(`teammate1@koat.or.kr` 등)을 실제 팀원 이메일로 수정
4. 우측 상단 **Run** 클릭 → `Success` 확인

> 표(`consultation_logs`, `allowed_members`)와 접근제한 정책(RLS)이 한 번에 만들어집니다.

### 3. 연결 정보 입력
1. 좌측 메뉴 **Project Settings**(톱니바퀴) → **API**
2. 아래 두 값을 복사
   - **Project URL** (예: `https://abcdxyz.supabase.co`)
   - **anon public** key (`eyJ...` 로 시작하는 긴 문자열)
3. **`index.html`** 을 열어 상단 `CONFIG` 부분을 수정:
   ```js
   const CONFIG = {
     SUPABASE_URL:      "https://abcdxyz.supabase.co",  // ← Project URL
     SUPABASE_ANON_KEY: "eyJhbGciOi...",                // ← anon public key
   };
   ```
4. 저장 후 커밋·푸시 → GitHub Pages 에 자동 반영

### 4. 팀원 계정 만들기 (2가지 방법 중 택1)
- **방법 A (권장) — 관리자가 초대**: Supabase → **Authentication → Users → Add user → Send invitation**.
  초대 이메일을 받은 팀원이 비밀번호를 설정하면 끝. 이후 무단 가입을 막으려면
  **Authentication → Sign In / Providers → Email → "Allow new users to sign up"** 를 꺼두세요.
- **방법 B — 팀원이 직접 가입**: 페이지에서 **최초 가입** 탭으로 이메일·비밀번호 가입 후 이메일 인증.

> ⚠️ 어느 방법이든, **`allowed_members` 허용목록에 이메일이 있어야만** 상담일지를 볼 수 있습니다.
> 가입만으로는 열람되지 않습니다(빈 화면/권한없음 안내).

---

## 팀원 추가 / 제거

Supabase → **SQL Editor** 또는 **Table editor → allowed_members** 에서 관리합니다.

```sql
-- 팀원 추가
insert into public.allowed_members (email, display_name)
values ('new.member@koat.or.kr', '홍길동');

-- 팀원 제거 (즉시 접근 차단)
delete from public.allowed_members where email = 'someone@koat.or.kr';
```

이메일은 **로그인에 사용하는 이메일과 정확히 동일**해야 합니다(대소문자는 자동으로 무시됩니다).

---

## 접근 페이지 주소

GitHub Pages(`/docs`) 배포 기준:

```
https://<GitHub계정>.github.io/<저장소>/consult/
```

검색엔진에 노출되지 않도록 `noindex` 가 걸려 있지만, **주소를 아는 것만으로 열람되지는 않습니다.**
로그인 + 허용목록 통과가 반드시 필요합니다.

---

## 보안 요약

| 항목 | 처리 방식 |
|------|-----------|
| 데이터 저장 위치 | Supabase 서버 DB (페이지 소스에 노출 안 됨) |
| 접근 제한 | 이메일 허용목록 + Row Level Security(RLS) |
| 허용목록에 없는 로그인 사용자 | 조회·작성 모두 서버가 거부 → "권한 없음" 안내 |
| 페이지에 노출되는 anon key | 공개 안전(보안은 서버 RLS 가 담당) |
| 검색엔진 노출 | `noindex, nofollow` 로 차단 |
| 통신 구간 | HTTPS 암호화 |

민감도가 더 높다면 Supabase 대시보드에서 (1) 공개 가입 비활성화, (2) 특정 이메일 도메인만 허용,
(3) 접근 로그 모니터링을 추가로 적용할 수 있습니다.

---

## 로컬 미리보기

```bash
# 저장소 루트에서
python3 -m http.server 8080 --directory docs
# 브라우저: http://localhost:8080/consult/
```
