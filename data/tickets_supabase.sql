-- Tabla de tickets (Supabase, proyecto poketubi-torneos). Ejecutar una vez en el SQL editor.
-- RLS activo sin políticas públicas: solo la app (clave de servicio) lee y escribe.
create table if not exists public.tickets (
  id uuid primary key,
  codigo text not null unique,
  creado timestamptz not null default now(),
  jugador text not null,
  categoria text not null,
  torneo text default '',
  rival text default '',
  asunto text not null,
  descripcion text not null,
  evidencia text default '',
  contacto text default '',
  estado text not null default 'Abierto',
  respuesta text default '',
  respondido timestamptz
);
alter table public.tickets enable row level security;
