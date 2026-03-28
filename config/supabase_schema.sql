create table if not exists public.users (
    id uuid primary key,
    email text not null unique
);

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

alter table public.users enable row level security;
alter table public.conversations enable row level security;
alter table public.actions enable row level security;

create policy "users can read own profile"
on public.users
for select
using (auth.uid() = id);

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

