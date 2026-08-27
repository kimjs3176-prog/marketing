-- ============================================================================
--  상담일지 공유 페이지 — Supabase 초기 설정 SQL
-- ----------------------------------------------------------------------------
--  실행 방법:
--    1) Supabase 프로젝트 → 좌측 메뉴 [SQL Editor] → [New query]
--    2) 이 파일 전체를 붙여넣고 [Run] 클릭
--  이 스크립트는 여러 번 실행해도 안전합니다(IF NOT EXISTS / OR REPLACE 사용).
-- ============================================================================


-- ────────────────────────────────────────────────────────────────────────
-- 1. 허용 팀원 목록 테이블 (email allowlist)
--    여기에 등록된 이메일만 상담일지에 접근할 수 있습니다.
-- ────────────────────────────────────────────────────────────────────────
create table if not exists public.allowed_members (
  email        text primary key,
  display_name text,
  added_at     timestamptz not null default now()
);

comment on table public.allowed_members is '상담일지 접근이 허용된 지정 팀원 이메일 목록';


-- ────────────────────────────────────────────────────────────────────────
-- 2. 상담일지 테이블
-- ────────────────────────────────────────────────────────────────────────
create table if not exists public.consultation_logs (
  id           uuid primary key default gen_random_uuid(),
  company_name text not null,                         -- 수요기업명
  consult_date date,                                  -- 상담일자
  category     text,                                  -- 분야(치유/식량/스마트농업 등)
  technology   text,                                  -- 관심/상담 기술
  counselor    text,                                  -- 상담자(담당자)
  content      text,                                  -- 상담 내용
  followup     text,                                  -- 후속조치/특이사항
  status       text not null default '진행중',         -- 진행상태
  author_email text not null default (auth.jwt() ->> 'email'),
  author_id    uuid          default auth.uid(),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

comment on table public.consultation_logs is '팀 공유 상담일지 (수요기업 1:1 기술상담 기록)';

create index if not exists consultation_logs_created_idx
  on public.consultation_logs (created_at desc);


-- updated_at 자동 갱신 트리거
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_consultation_logs_updated on public.consultation_logs;
create trigger trg_consultation_logs_updated
  before update on public.consultation_logs
  for each row execute function public.set_updated_at();


-- ────────────────────────────────────────────────────────────────────────
-- 3. "현재 로그인 사용자가 허용된 팀원인가?" 판별 함수
--    RLS 정책의 핵심입니다. 로그인 사용자의 이메일이 allowed_members에
--    있어야만 true 를 반환합니다.
-- ────────────────────────────────────────────────────────────────────────
create or replace function public.is_allowed_member()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.allowed_members m
    where lower(m.email) = lower(auth.jwt() ->> 'email')
  );
$$;


-- ────────────────────────────────────────────────────────────────────────
-- 4. Row Level Security (RLS) — 실제 접근 제한이 여기서 이루어집니다.
--    RLS 를 켜면 정책에 부합하지 않는 요청은 서버가 거부합니다.
--    → 허용목록에 없는 사람은 anon key 를 알아도 데이터를 못 봅니다.
-- ────────────────────────────────────────────────────────────────────────
alter table public.consultation_logs enable row level security;
alter table public.allowed_members    enable row level security;

-- 상담일지: 허용된 팀원만 조회/작성/수정/삭제 가능
drop policy if exists "logs_select_allowed" on public.consultation_logs;
create policy "logs_select_allowed" on public.consultation_logs
  for select using ( public.is_allowed_member() );

drop policy if exists "logs_insert_allowed" on public.consultation_logs;
create policy "logs_insert_allowed" on public.consultation_logs
  for insert with check ( public.is_allowed_member() );

drop policy if exists "logs_update_allowed" on public.consultation_logs;
create policy "logs_update_allowed" on public.consultation_logs
  for update using ( public.is_allowed_member() )
              with check ( public.is_allowed_member() );

drop policy if exists "logs_delete_allowed" on public.consultation_logs;
create policy "logs_delete_allowed" on public.consultation_logs
  for delete using ( public.is_allowed_member() );

-- 허용목록: 허용된 팀원은 "누가 팀에 있는지" 조회만 가능.
--          추가/삭제(팀원 관리)는 대시보드(서비스 롤)에서만 하도록
--          클라이언트 쓰기 정책은 두지 않습니다.
drop policy if exists "members_select_allowed" on public.allowed_members;
create policy "members_select_allowed" on public.allowed_members
  for select using ( public.is_allowed_member() );


-- ────────────────────────────────────────────────────────────────────────
-- 5. 지정 팀원 등록
--    ★ 아래 이메일을 실제 팀원 이메일로 바꾸고 필요한 만큼 추가하세요.
--    ★ 반드시 소문자로, 실제 로그인에 사용할 이메일과 동일하게 입력하세요.
-- ────────────────────────────────────────────────────────────────────────
insert into public.allowed_members (email, display_name) values
  ('teammate1@koat.or.kr', '팀원1'),
  ('teammate2@koat.or.kr', '팀원2')
on conflict (email) do nothing;

-- 팀원 추가 예시 (나중에 SQL Editor 나 Table editor 에서):
--   insert into public.allowed_members (email, display_name)
--   values ('new.member@koat.or.kr', '새 팀원');
-- 팀원 제거:
--   delete from public.allowed_members where email = 'someone@koat.or.kr';

-- ────────────────────────────────────────────────────────────────────────
-- 6. 실시간(Realtime) 활성화
--    팀원이 상담일지를 추가/수정하면 다른 팀원 화면에 즉시 반영되도록
--    테이블을 realtime publication 에 추가합니다. (이미 추가돼 있으면 건너뜀)
-- ────────────────────────────────────────────────────────────────────────
do $$
begin
  begin
    alter publication supabase_realtime add table public.consultation_logs;
  exception
    when duplicate_object then null;  -- 이미 추가됨
    when undefined_object then null;  -- publication 이 없는 특수 환경
  end;
end $$;

-- ============================================================================
--  설정 완료. 이제 docs/consult/index.html 상단 CONFIG 에
--  프로젝트 URL 과 anon key 를 입력하면 됩니다.
-- ============================================================================
