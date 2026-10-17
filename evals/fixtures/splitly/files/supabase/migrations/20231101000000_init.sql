create table profiles (
  id uuid primary key references auth.users on delete cascade,
  email text,
  full_name text,
  phone text,
  is_pro boolean default false,
  created_at timestamptz default now()
);

alter table profiles enable row level security;
create policy "Profiles are viewable by everyone" on profiles for select using (true);
create policy "Users can update own profile" on profiles for update using (auth.uid() = id);

create table groups (
  id bigint generated always as identity primary key,
  name text not null,
  created_by uuid references profiles(id),
  created_at timestamptz default now()
);

create table group_members (
  group_id bigint references groups(id) on delete cascade,
  user_id uuid references profiles(id) on delete cascade,
  primary key (group_id, user_id)
);

create table expenses (
  id bigint generated always as identity primary key,
  group_id bigint references groups(id) on delete cascade,
  description text,
  amount integer not null,
  paid_by uuid references profiles(id),
  split_between uuid[],
  created_at timestamptz default now()
);

create table comments (
  id bigint generated always as identity primary key,
  group_id bigint references groups(id) on delete cascade,
  author_name text,
  body text,
  created_at timestamptz default now()
);

create table invites (
  id bigint generated always as identity primary key,
  email text,
  group_id bigint references groups(id) on delete cascade,
  token text,
  created_at timestamptz default now()
);

insert into storage.buckets (id, name, public) values ('receipts', 'receipts', true);
