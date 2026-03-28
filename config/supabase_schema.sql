create extension if not exists pgcrypto;

create table if not exists public.users (
    id uuid primary key,
    email text not null unique
);

alter table public.users
    add column if not exists name text,
    add column if not exists picture_url text,
    add column if not exists provider text not null default 'google',
    add column if not exists role text not null default 'user',
    add column if not exists google_sub text unique,
    add column if not exists system_prompt text not null default '',
    add column if not exists device_access_enabled boolean not null default false,
    add column if not exists device_access_configured boolean not null default false,
    add column if not exists created_at timestamptz not null default timezone('utc', now()),
    add column if not exists last_login_at timestamptz not null default timezone('utc', now());

create table if not exists public.conversations (
    id bigint generated always as identity primary key,
    user_id uuid not null references public.users(id) on delete cascade,
    message text not null,
    response text not null,
    timestamp timestamptz not null default timezone('utc', now())
);

create table if not exists public.actions (
    id bigint generated always as identity primary key,
    user_id uuid not null references public.users(id) on delete cascade,
    action_type text not null,
    details jsonb not null default '{}'::jsonb,
    timestamp timestamptz not null default timezone('utc', now())
);

create index if not exists idx_conversations_user_id on public.conversations(user_id);
create index if not exists idx_actions_user_id on public.actions(user_id);

alter table public.users enable row level security;
alter table public.conversations enable row level security;
alter table public.actions enable row level security;

drop policy if exists "users can read own profile" on public.users;
drop policy if exists "users can update own profile" on public.users;
drop policy if exists "users can read own conversations" on public.conversations;
drop policy if exists "users can insert own conversations" on public.conversations;
drop policy if exists "users can read own actions" on public.actions;
drop policy if exists "users can insert own actions" on public.actions;

create policy "users can read own profile"
on public.users
for select
using (auth.uid() = id);

create policy "users can update own profile"
on public.users
for update
using (auth.uid() = id)
with check (auth.uid() = id);

create policy "users can read own conversations"
on public.conversations
for select
using (auth.uid() = user_id);

create policy "users can insert own conversations"
on public.conversations
for insert
with check (auth.uid() = user_id);

create policy "users can read own actions"
on public.actions
for select
using (auth.uid() = user_id);

create policy "users can insert own actions"
on public.actions
for insert
with check (auth.uid() = user_id);
