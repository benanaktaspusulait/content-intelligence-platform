INSERT INTO characters(id,name,status,notes,active)
VALUES
  ('00000000-0000-0000-0000-000000000001','Opa','UNTESTED','Season 1 canonical character',true),
  ('00000000-0000-0000-0000-000000000002','Kiko','UNTESTED','Season 1 canonical character',true),
  ('00000000-0000-0000-0000-000000000003','Mimi','UNTESTED','Season 1 canonical character',true),
  ('00000000-0000-0000-0000-000000000004','Arda','UNTESTED','Season 1 canonical character',true),
  ('00000000-0000-0000-0000-000000000005','Luca','UNTESTED','Season 1 canonical character',true),
  ('00000000-0000-0000-0000-000000000006','Noah','UNTESTED','Season 1 canonical character',true)
ON CONFLICT (name) DO NOTHING;
