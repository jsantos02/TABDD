------------------------------------------------------------
-- LINES: Metro (A, D, E) + Bus (500, 600, 901)
------------------------------------------------------------

INSERT INTO lines (line_id, code, name, line_mode, active) VALUES
  ('LINE_M_A',   'A',   'Linha Azul: Estádio do Dragão - Senhor de Matosinhos', 'metro', 1);

INSERT INTO lines (line_id, code, name, line_mode, active) VALUES
  ('LINE_M_D',   'D',   'Linha Amarela: Hospital São João - Santo Ovídio',     'metro', 1);

INSERT INTO lines (line_id, code, name, line_mode, active) VALUES
  ('LINE_M_E',   'E',   'Linha Violeta: Estádio do Dragão - Aeroporto',        'metro', 1);

INSERT INTO lines (line_id, code, name, line_mode, active) VALUES
  ('LINE_B_500', '500', 'STCP 500: Aliados - Matosinhos (via Foz)',            'bus',   1);

INSERT INTO lines (line_id, code, name, line_mode, active) VALUES
  ('LINE_B_600', '600', 'STCP 600: Hospital São João - Aliados - Maia',        'bus',   1);

INSERT INTO lines (line_id, code, name, line_mode, active) VALUES
  ('LINE_B_901', '901', 'STCP 901: Trindade - Vila Nova de Gaia',              'bus',   1);



------------------------------------------------------------
-- STOPS: Metro (M_*) and Bus (B_*) with real coordinates
------------------------------------------------------------

-- METRO STOPS (M_*)

INSERT ALL
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_DRAGAO',         'M-DRAG',  'Estádio do Dragão (Metro)',               41.161758, -8.583933)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_CAMPANHA',       'M-CAMP',  'Campanhã (Metro)',                        41.151000, -8.585500)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_HEROISIMO',      'M-HERO',  'Heroísmo (Metro)',                        41.144170, -8.587500)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_CAMPO24',        'M-C24A',  'Campo 24 de Agosto (Metro)',              41.146390, -8.597500)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_BOLHAO',         'M-BOLH',  'Bolhão (Metro)',                          41.148710, -8.605670)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_TRINDADE',       'M-TRIN',  'Trindade (Metro)',                        41.152200, -8.609100)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_LAPA',           'M-LAPA',  'Lapa (Metro)',                            41.156670, -8.617500)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_CAROLINA',       'M-CMCH',  'Carolina Michaëlis (Metro)',              41.159440, -8.623890)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_CASA_MUSICA',    'M-CDM',   'Casa da Música (Metro)',                  41.162130, -8.630500)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_FRANCOS',        'M-FRAN',  'Francos (Metro)',                         41.174170, -8.610280)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_RAMALDE',        'M-RAMA',  'Ramalde (Metro)',                         41.177220, -8.618610)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_SENHORA_HORA',   'M-SHORA', 'Senhora da Hora (Metro)',                 41.175830, -8.651390)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_PEDRAS_RUBRAS',  'M-PEDR',  'Pedras Rubras (Metro)',                   41.242500, -8.678330)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_SENHOR_MATOS',   'M-SMAT',  'Senhor de Matosinhos (Metro)',            41.188200, -8.685080)

  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_HOSP_S_JOAO',    'M-HSJ',   'Hospital São João (Metro)',               41.184640, -8.602330)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_IPO',            'M-IPO',   'IPO (Metro)',                             41.182500, -8.596670)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_POLO_UNIV',      'M-PUNIV', 'Pólo Universitário (Metro)',              41.178060, -8.592780)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_SALGUEIROS',     'M-SALG',  'Salgueiros (Metro)',                      41.173060, -8.593610)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_COMBATENTES',    'M-COMB',  'Combatentes (Metro)',                     41.167220, -8.596390)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_MARQUES',        'M-MARQ',  'Marquês (Metro)',                         41.162220, -8.600280)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_FARIA_GUIM',     'M-FG',    'Faria Guimarães (Metro)',                 41.157500, -8.605000)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_ALIADOS',        'M-ALIA',  'Aliados (Metro)',                         41.148330, -8.610000)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_SAO_BENTO',      'M-SBEN',  'São Bento (Metro)',                       41.144900, -8.610830)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_JARDIM_MORRO',   'M-JMOR',  'Jardim do Morro (Metro)',                 41.139420, -8.609500)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_GENERAL_TORRES', 'M-GTOR',  'General Torres (Metro)',                  41.134030, -8.607500)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_CAMARA_GAIA',    'M-CGAIA', 'Câmara de Gaia (Metro)',                  41.133500, -8.608300)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_JOAO_DE_DEUS',   'M-JDEUS', 'João de Deus (Metro)',                    41.126050, -8.605640)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_DOM_JOAO_II',    'M-DJ2',   'Dom João II (Metro)',                     41.119720, -8.608060)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_SANTO_OVIDIO',   'M-SOVID', 'Santo Ovídio (Metro)',                    41.124720, -8.611940)

  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_AEROPORTO',      'M-AIRP',  'Aeroporto Francisco Sá Carneiro (Metro)', 41.235280, -8.678890)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('M_STOP_VERDES',         'M-VERD',  'Verdes (Metro)',                          41.235280, -8.681110)
SELECT 1 FROM dual;


-- BUS STOPS (B_*) – independent rows, but often same coordinates
-- as the corresponding square/area (Aliados, São Bento, etc.)

INSERT ALL
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_ALIADOS',          'B-ALIA', 'Aliados (Bus)',                 41.148330, -8.610000)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_SAO_BENTO',        'B-SBEN', 'São Bento (Bus)',               41.145670, -8.609590)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_RIBEIRA',          'B-RIB',  'Ribeira (Bus)',                 41.140579, -8.611365)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_FOZ',              'B-FOZ',  'Foz (Praia da Luz) (Bus)',      41.153453, -8.679470)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_MATOSINHOS_PRAIA', 'B-MAT',  'Matosinhos (Praia) (Bus)',      41.175916, -8.694136)

  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_HOSP_S_JOAO',      'B-HSJ',  'Hospital São João (Bus)',       41.184640, -8.602330)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_POLO_UNIV',        'B-PUNIV','Pólo Universitário (Bus)',      41.178060, -8.592780)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_MARQUES',          'B-MARQ', 'Marquês (Bus)',                 41.162220, -8.600280)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_MAIA_SHOPPING',    'B-MAIA', 'Maia Shopping (Bus)',           41.255983, -8.653624)

  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_TRINDADE',         'B-TRIN', 'Trindade (Bus)',                41.152200, -8.609100)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_JARDIM_MORRO',     'B-JMOR', 'Jardim do Morro (Bus)',         41.139420, -8.609500)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_GAIA_CAIS',        'B-GCAIS','Cais de Gaia (Bus)',            41.137621, -8.617253)
  INTO stops (stop_id, code, name, lat, lon) VALUES
    ('B_STOP_SANTO_OVIDIO',     'B-SOVID','Santo Ovídio (Bus)',           41.124720, -8.611940)
SELECT 1 FROM dual;


------------------------------------------------------------
-- METRO ITINERARIES (stop_times for LINE_M_A, LINE_M_D, LINE_M_E)
------------------------------------------------------------

-- LINE_M_A: Estádio do Dragão -> Senhor de Matosinhos

INSERT ALL
  INTO stop_times (stop_time_id, line_id, stop_id, scheduled_seconds_from_start)
    VALUES ('ST_LINE_M_A_01', 'LINE_M_A', 'M_STOP_DRAGAO',           0)
  INTO stop_times VALUES ('ST_LINE_M_A_02', 'LINE_M_A', 'M_STOP_CAMPANHA',       300)
  INTO stop_times VALUES ('ST_LINE_M_A_03', 'LINE_M_A', 'M_STOP_HEROISIMO',      600)
  INTO stop_times VALUES ('ST_LINE_M_A_04', 'LINE_M_A', 'M_STOP_CAMPO24',        900)
  INTO stop_times VALUES ('ST_LINE_M_A_05', 'LINE_M_A', 'M_STOP_BOLHAO',        1200)
  INTO stop_times VALUES ('ST_LINE_M_A_06', 'LINE_M_A', 'M_STOP_TRINDADE',      1500)
  INTO stop_times VALUES ('ST_LINE_M_A_07', 'LINE_M_A', 'M_STOP_LAPA',          1800)
  INTO stop_times VALUES ('ST_LINE_M_A_08', 'LINE_M_A', 'M_STOP_CAROLINA',      2100)
  INTO stop_times VALUES ('ST_LINE_M_A_09', 'LINE_M_A', 'M_STOP_CASA_MUSICA',   2400)
  INTO stop_times VALUES ('ST_LINE_M_A_10', 'LINE_M_A', 'M_STOP_FRANCOS',       2700)
  INTO stop_times VALUES ('ST_LINE_M_A_11', 'LINE_M_A', 'M_STOP_RAMALDE',       3000)
  INTO stop_times VALUES ('ST_LINE_M_A_12', 'LINE_M_A', 'M_STOP_SENHORA_HORA',  3300)
  INTO stop_times VALUES ('ST_LINE_M_A_13', 'LINE_M_A', 'M_STOP_PEDRAS_RUBRAS', 3600)
  INTO stop_times VALUES ('ST_LINE_M_A_14', 'LINE_M_A', 'M_STOP_SENHOR_MATOS',  3900)
SELECT 1 FROM dual;



-- LINE_M_D: Hospital São João -> Santo Ovídio

INSERT ALL
  INTO stop_times VALUES ('ST_LINE_M_D_01', 'LINE_M_D', 'M_STOP_HOSP_S_JOAO',   0)
  INTO stop_times VALUES ('ST_LINE_M_D_02', 'LINE_M_D', 'M_STOP_IPO',          300)
  INTO stop_times VALUES ('ST_LINE_M_D_03', 'LINE_M_D', 'M_STOP_POLO_UNIV',    600)
  INTO stop_times VALUES ('ST_LINE_M_D_04', 'LINE_M_D', 'M_STOP_SALGUEIROS',   900)
  INTO stop_times VALUES ('ST_LINE_M_D_05', 'LINE_M_D', 'M_STOP_COMBATENTES', 1200)
  INTO stop_times VALUES ('ST_LINE_M_D_06', 'LINE_M_D', 'M_STOP_MARQUES',     1500)
  INTO stop_times VALUES ('ST_LINE_M_D_07', 'LINE_M_D', 'M_STOP_FARIA_GUIM',  1800)
  INTO stop_times VALUES ('ST_LINE_M_D_08', 'LINE_M_D', 'M_STOP_TRINDADE',    2100)
  INTO stop_times VALUES ('ST_LINE_M_D_09', 'LINE_M_D', 'M_STOP_ALIADOS',     2400)
  INTO stop_times VALUES ('ST_LINE_M_D_10', 'LINE_M_D', 'M_STOP_SAO_BENTO',   2700)
  INTO stop_times VALUES ('ST_LINE_M_D_11', 'LINE_M_D', 'M_STOP_JARDIM_MORRO',3000)
  INTO stop_times VALUES ('ST_LINE_M_D_12', 'LINE_M_D', 'M_STOP_GENERAL_TORRES',3300)
  INTO stop_times VALUES ('ST_LINE_M_D_13', 'LINE_M_D', 'M_STOP_CAMARA_GAIA', 3600)
  INTO stop_times VALUES ('ST_LINE_M_D_14', 'LINE_M_D', 'M_STOP_JOAO_DE_DEUS',3900)
  INTO stop_times VALUES ('ST_LINE_M_D_15', 'LINE_M_D', 'M_STOP_DOM_JOAO_II', 4200)
  INTO stop_times VALUES ('ST_LINE_M_D_16', 'LINE_M_D', 'M_STOP_SANTO_OVIDIO',4500)
SELECT 1 FROM dual;


-- LINE_M_E: Aeroporto -> Estádio do Dragão

INSERT ALL
  INTO stop_times (stop_time_id, line_id, stop_id, scheduled_seconds_from_start)
    VALUES ('ST_LINE_M_E_01', 'LINE_M_E', 'M_STOP_AEROPORTO',       0)
  INTO stop_times VALUES ('ST_LINE_M_E_02', 'LINE_M_E', 'M_STOP_VERDES',        300)
  INTO stop_times VALUES ('ST_LINE_M_E_03', 'LINE_M_E', 'M_STOP_PEDRAS_RUBRAS', 600)
  INTO stop_times VALUES ('ST_LINE_M_E_04', 'LINE_M_E', 'M_STOP_SENHORA_HORA',  900)
  INTO stop_times VALUES ('ST_LINE_M_E_05', 'LINE_M_E', 'M_STOP_RAMALDE',      1200)
  INTO stop_times VALUES ('ST_LINE_M_E_06', 'LINE_M_E', 'M_STOP_CASA_MUSICA',  1500)
  INTO stop_times VALUES ('ST_LINE_M_E_07', 'LINE_M_E', 'M_STOP_CAROLINA',     1800)
  INTO stop_times VALUES ('ST_LINE_M_E_08', 'LINE_M_E', 'M_STOP_LAPA',         2100)
  INTO stop_times VALUES ('ST_LINE_M_E_09', 'LINE_M_E', 'M_STOP_TRINDADE',     2400)
  INTO stop_times VALUES ('ST_LINE_M_E_10', 'LINE_M_E', 'M_STOP_BOLHAO',       2700)
  INTO stop_times VALUES ('ST_LINE_M_E_11', 'LINE_M_E', 'M_STOP_CAMPO24',      3000)
  INTO stop_times VALUES ('ST_LINE_M_E_12', 'LINE_M_E', 'M_STOP_HEROISIMO',    3300)
  INTO stop_times VALUES ('ST_LINE_M_E_13', 'LINE_M_E', 'M_STOP_CAMPANHA',     3600)
  INTO stop_times VALUES ('ST_LINE_M_E_14', 'LINE_M_E', 'M_STOP_DRAGAO',       3900)
SELECT 1 FROM dual;


------------------------------------------------------------
-- BUS ITINERARIES (stop_times for LINE_B_500, LINE_B_600, LINE_B_901)
------------------------------------------------------------

-- LINE_B_500: Aliados (Bus) -> Matosinhos Praia (Bus)
-- Aliados (Bus) -> São Bento (Bus) -> Ribeira -> Foz -> Matosinhos Praia

INSERT ALL
  INTO stop_times VALUES ('ST_LINE_B_500_01', 'LINE_B_500', 'B_STOP_ALIADOS',          0)
  INTO stop_times VALUES ('ST_LINE_B_500_02', 'LINE_B_500', 'B_STOP_SAO_BENTO',      420)
  INTO stop_times VALUES ('ST_LINE_B_500_03', 'LINE_B_500', 'B_STOP_RIBEIRA',        840)
  INTO stop_times VALUES ('ST_LINE_B_500_04', 'LINE_B_500', 'B_STOP_FOZ',           1260)
  INTO stop_times VALUES ('ST_LINE_B_500_05', 'LINE_B_500', 'B_STOP_MATOSINHOS_PRAIA',1680)
SELECT 1 FROM dual;


-- LINE_B_600: Hospital São João (Bus) -> Maia Shopping (Bus)
-- HSJ (Bus) -> Pólo Univ (Bus) -> Marquês (Bus) -> Aliados (Bus) -> Maia Shopping (Bus)

INSERT ALL
  INTO stop_times VALUES ('ST_LINE_B_600_01', 'LINE_B_600', 'B_STOP_HOSP_S_JOAO',    0)
  INTO stop_times VALUES ('ST_LINE_B_600_02', 'LINE_B_600', 'B_STOP_POLO_UNIV',    420)
  INTO stop_times VALUES ('ST_LINE_B_600_03', 'LINE_B_600', 'B_STOP_MARQUES',      840)
  INTO stop_times VALUES ('ST_LINE_B_600_04', 'LINE_B_600', 'B_STOP_ALIADOS',     1260)
  INTO stop_times VALUES ('ST_LINE_B_600_05', 'LINE_B_600', 'B_STOP_MAIA_SHOPPING',1680)
SELECT 1 FROM dual;


-- LINE_B_901: Trindade (Bus) -> Santo Ovídio (Bus)
-- Trindade (Bus) -> São Bento (Bus) -> Jardim do Morro (Bus) -> Cais de Gaia (Bus) -> Santo Ovídio (Bus)

INSERT ALL
  INTO stop_times VALUES ('ST_LINE_B_901_01', 'LINE_B_901', 'B_STOP_TRINDADE',       0)
  INTO stop_times VALUES ('ST_LINE_B_901_02', 'LINE_B_901', 'B_STOP_SAO_BENTO',    420)
  INTO stop_times VALUES ('ST_LINE_B_901_03', 'LINE_B_901', 'B_STOP_JARDIM_MORRO',840)
  INTO stop_times VALUES ('ST_LINE_B_901_04', 'LINE_B_901', 'B_STOP_GAIA_CAIS',   1260)
  INTO stop_times VALUES ('ST_LINE_B_901_05', 'LINE_B_901', 'B_STOP_SANTO_OVIDIO',1680)
SELECT 1 FROM dual;


------------------------------------------------------------
-- LINE SCHEDULES (simple weekday headways)
------------------------------------------------------------

INSERT ALL
  -- Metro A
  INTO line_schedules (schedule_id, line_id, dow, start_time, end_time, headway_minutes)
    VALUES ('LS_LINE_M_A_1', 'LINE_M_A', 1,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)
  INTO line_schedules VALUES ('LS_LINE_M_A_2', 'LINE_M_A', 2,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)
  INTO line_schedules VALUES ('LS_LINE_M_A_3', 'LINE_M_A', 3,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)
  INTO line_schedules VALUES ('LS_LINE_M_A_4', 'LINE_M_A', 4,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)
  INTO line_schedules VALUES ('LS_LINE_M_A_5', 'LINE_M_A', 5,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)

  -- Metro D
  INTO line_schedules VALUES ('LS_LINE_M_D_1', 'LINE_M_D', 1,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)
  INTO line_schedules VALUES ('LS_LINE_M_D_2', 'LINE_M_D', 2,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)
  INTO line_schedules VALUES ('LS_LINE_M_D_3', 'LINE_M_D', 3,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)
  INTO line_schedules VALUES ('LS_LINE_M_D_4', 'LINE_M_D', 4,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)
  INTO line_schedules VALUES ('LS_LINE_M_D_5', 'LINE_M_D', 5,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)

  -- Metro E
  INTO line_schedules VALUES ('LS_LINE_M_E_1', 'LINE_M_E', 1,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)
  INTO line_schedules VALUES ('LS_LINE_M_E_2', 'LINE_M_E', 2,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)
  INTO line_schedules VALUES ('LS_LINE_M_E_3', 'LINE_M_E', 3,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)
  INTO line_schedules VALUES ('LS_LINE_M_E_4', 'LINE_M_E', 4,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)
  INTO line_schedules VALUES ('LS_LINE_M_E_5', 'LINE_M_E', 5,
            TO_DATE('06:00','HH24:MI'), TO_DATE('23:00','HH24:MI'), 10)

  -- Bus 500
  INTO line_schedules VALUES ('LS_LINE_B_500_1', 'LINE_B_500', 1,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
  INTO line_schedules VALUES ('LS_LINE_B_500_2', 'LINE_B_500', 2,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
  INTO line_schedules VALUES ('LS_LINE_B_500_3', 'LINE_B_500', 3,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
  INTO line_schedules VALUES ('LS_LINE_B_500_4', 'LINE_B_500', 4,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
  INTO line_schedules VALUES ('LS_LINE_B_500_5', 'LINE_B_500', 5,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)

  -- Bus 600
  INTO line_schedules VALUES ('LS_LINE_B_600_1', 'LINE_B_600', 1,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
  INTO line_schedules VALUES ('LS_LINE_B_600_2', 'LINE_B_600', 2,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
  INTO line_schedules VALUES ('LS_LINE_B_600_3', 'LINE_B_600', 3,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
  INTO line_schedules VALUES ('LS_LINE_B_600_4', 'LINE_B_600', 4,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
  INTO line_schedules VALUES ('LS_LINE_B_600_5', 'LINE_B_600', 5,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)

  -- Bus 901
  INTO line_schedules VALUES ('LS_LINE_B_901_1', 'LINE_B_901', 1,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
  INTO line_schedules VALUES ('LS_LINE_B_901_2', 'LINE_B_901', 2,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
  INTO line_schedules VALUES ('LS_LINE_B_901_3', 'LINE_B_901', 3,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
  INTO line_schedules VALUES ('LS_LINE_B_901_4', 'LINE_B_901', 4,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
  INTO line_schedules VALUES ('LS_LINE_B_901_5', 'LINE_B_901', 5,
            TO_DATE('06:00','HH24:MI'), TO_DATE('22:00','HH24:MI'), 15)
SELECT 1 FROM dual;
