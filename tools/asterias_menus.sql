-- Piato · Asterias — Cohilia (νέο outlet) + Oliva drinks (κατηγορίες στο Oliva)
-- Paste στο Railway psql. Idempotent (per-category). Draft.
DO $$
DECLARE v_hotel int; v_outlet int; v_cat int; v_item int;
BEGIN
  SELECT id INTO v_hotel FROM hotel WHERE name ILIKE '%asterias%' ORDER BY id LIMIT 1;
  IF v_hotel IS NULL THEN RAISE EXCEPTION 'Asterias not found'; END IF;
  -- OLIVA (existing outlet) -> drink categories
  SELECT id INTO v_outlet FROM piato_outlet WHERE hotel_id=v_hotel AND name ILIKE '%oliva%' ORDER BY id LIMIT 1;
  IF v_outlet IS NULL THEN RAISE EXCEPTION 'Oliva outlet not found'; END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Aperitifs"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Aperitifs"}','',true,10,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Raki Shot | Carafe 120ml"}','{"en": "€2 | €6"}',2.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Ouzo Glass | Bottle 200ml"}','{"en": "€4.5 | €14"}',4.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Martini Bianco"}','{"en": ""}',5.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Martini Dry"}','{"en": ""}',5.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Campari"}','{"en": ""}',5.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Aperol"}','{"en": ""}',5.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Sparkling"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Sparkling"}','',true,11,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Prosecco Glass | Bottle"}','{"en": "€6 | €30"}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Moscato D’ Asti Glass | Bottle"}','{"en": "€6 | €30"}',6.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Aperol Spritz"}','{"en": ""}',8.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Kir Royal"}','{"en": ""}',8.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Mimosa"}','{"en": ""}',8.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Beers"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Beers"}','',true,12,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Amstel free 330 0%"}','{"en": ""}',4.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Draft Mythos 300 5%"}','{"en": ""}',4.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Draft Mythos 500 5%"}','{"en": ""}',5.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Mythos 330 5%"}','{"en": ""}',4.50,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Amstel 330 5%"}','{"en": ""}',4.50,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Heineken 3305%"}','{"en": ""}',4.50,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Erdinger Weiss 500 5.3 %"}','{"en": ""}',8.00,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "White Wine"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "White Wine"}','',true,13,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "House Lyrarakis 2024"}','{"en": "Glass | Carafe 500ml | Carafe 1L · €5 | €8 | €14"}',5.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Savignon Blanc Local Cretan 2025"}','{"en": "Glass | Bottle · €5 | €30"}',5.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Marmaromenos Vasilias Asyrtiko 2024"}','{"en": "Glass | Bottle · €6 | €35"}',6.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Little Angel Thrapsathiri Vidiano Awarded of Crete"}','{"en": "€7 | €40"}',7.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Plyto Rare Local Crete Fruity Variety 2025"}','{"en": "€8 | €45"}',8.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Asyrtiko Terra Divino Awarded of Crete 2025"}','{"en": "€9 | €50"}',9.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Chardonnay Terra Divino Winery of Crete 2025"}','{"en": "€9 | €50"}',9.00,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Red Wine"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Red Wine"}','',true,14,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "House Lyrarakis 2024"}','{"en": "Glass | Carafe 500ml | Carafe 1L · €5 | €8 | €14"}',5.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Merlot Terra Divino Winery of Crete 2024"}','{"en": "€5 | €30"}',5.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Little Angel Kotsifali Cabernet Sauvignon 24"}','{"en": "Glass | Bottle · €7 | €40"}',7.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Portes Skoyras Merlot 2023"}','{"en": "Glass | Bottle · €7 | €40"}',7.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Rose"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Rose"}','',true,15,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "House Lyrarakis 2024"}','{"en": "Glass | Carafe 500ml | Carafe 1L · €5 | €8 | €14"}',5.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Dafnios Vidiano 2025"}','{"en": "Glass | Bottle · €6 | €35"}',6.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Maskes Merlot 2023"}','{"en": "Glass | Bottle · €8 | €45"}',8.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Peplo Syrah 2023"}','{"en": "Glass | Bottle · €9 | €50"}',9.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Little Angel Rose 2025 Liatiko -syrah Awarded Wine"}','{"en": "€9 | €50"}',9.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Sirines Rose 2025 Medium Dry Grenache Rouge Liatiko"}','{"en": "€9 | €50"}',9.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Spirits"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Spirits"}','',true,16,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Gordon’s"}','{"en": ""}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Gordon’s Premium Pink"}','{"en": ""}',7.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Hendrick’s"}','{"en": ""}',10.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Smirnoff"}','{"en": ""}',6.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Stoli"}','{"en": ""}',6.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Gray Goose"}','{"en": ""}',10.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Bacardi Carta Bianca"}','{"en": ""}',6.00,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Havana Black"}','{"en": ""}',7.00,'',true,8,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Hose Cuervo Silver"}','{"en": ""}',7.00,'',true,9,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Hose Curvo Gold"}','{"en": ""}',7.00,'',true,10,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Long Drinks"}','{"en": "Regular | Premium · €8 | €11"}',8.00,'',true,11,now(),now()) RETURNING id INTO v_item;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Cocktails"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Cocktails"}','',true,17,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Mojito"}','{"en": "White rum, Lime juice, White sugar, Mint leaves, Soda"}',10.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Pina Colada"}','{"en": "Coconut juice, Pineapple and White rum"}',10.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Sex on the Beach"}','{"en": "Vodka, Cranberry juice, and Black raspberry liqueur"}',10.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Caipirinha"}','{"en": "Cachaça, Lime, and Sugar"}',10.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Margarita"}','{"en": "Tequila, Lime and Triple sec"}',10.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Daiquiri"}','{"en": "Rum, Lime juice, and Sugar syrup"}',10.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Mai Tai"}','{"en": "Rum, Curaçao liqueur, Orgeat syrup, and Lime juice"}',10.00,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Bramblε"}','{"en": "Gin, Fresh lemon juice, Simple syrup and Creme de murre"}',10.00,'',true,8,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "White Sangria"}','{"en": "Secret Recipe"}',10.00,'',true,9,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Kids Menu"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Kids Menu"}','',true,18,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Spaghetti Napolitana"}','{"en": "With cheese"}',5.50,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Spaghetti Bolognese"}','{"en": "With cheese"}',6.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Chicken Nuggets"}','{"en": "With chips and a dip of Ketchup"}',6.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Plain Burger"}','{"en": "With chips and a dip of Ketchup"}',6.50,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Brandy"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Brandy"}','',true,19,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Metaxa 3* 33%"}','{"en": ""}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Metaxa 5* 40%"}','{"en": ""}',7.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Metaxa 7* 38%"}','{"en": ""}',9.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Hennessy Vs"}','{"en": "Cognac 40%"}',14.00,'',true,4,now(),now()) RETURNING id INTO v_item;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Whiskey"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Whiskey"}','',true,20,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Johnnie Walker"}','{"en": "Red label Scotch blend 40%"}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Famus Grouse"}','{"en": "Scotch Blend 40%"}',6.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "J&B"}','{"en": "Scotch Blend 40%"}',7.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Ballantine’s"}','{"en": "Scotch Blend 40%"}',7.50,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Dewar’s"}','{"en": "White label Scotch Blend 40%"}',7.50,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Cutty Sark"}','{"en": "Scotch Blend 40%"}',7.50,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Jameson"}','{"en": "Irish Blend 40%"}',7.50,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Jack Daniel’s"}','{"en": "Tennessee Bourbon Whiskey old No 7 40%"}',7.50,'',true,8,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Chivas Regal 12 12"}','{"en": "Year Old Scotch Blend 40%"}',8.00,'',true,9,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Dimple"}','{"en": "Scotch Blend 15 Years Old 40%"}',8.00,'',true,10,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Johnnie Walker"}','{"en": "Black barrel Scotch Blend 12 Years 40%"}',9.00,'',true,11,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Cardhu 12"}','{"en": "Single Malt 12 Year Old Whiskey 40%"}',10.00,'',true,12,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Glenfiddich"}','{"en": "Single Malt 12 Year Old Whiskey 40%"}',13.00,'',true,13,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Lagavulin 16"}','{"en": "single malt Scotch smoked Whiskey 43%"}',15.00,'',true,14,now(),now()) RETURNING id INTO v_item;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Refreshments & Coffee"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Refreshments & Coffee"}','',true,21,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Soft Drinks"}','{"en": ""}',3.50,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Mineral Water 0.5L."}','{"en": ""}',1.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Mineral Water 1L."}','{"en": ""}',2.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Sparkling Water 1L."}','{"en": ""}',3.50,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Ice Tea Lemon/peach"}','{"en": ""}',4.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Amita Juice Orange/apple/cherry/pineapple"}','{"en": ""}',4.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Fresh Orange Juice"}','{"en": ""}',5.00,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Homemade Lamonade or Sour Cherry"}','{"en": ""}',5.00,'',true,8,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Milkshake"}','{"en": ""}',5.00,'',true,9,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Greek Coffee"}','{"en": "Single | Double · €3 | €4"}',3.00,'',true,10,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Espresso"}','{"en": "Single | Double · €3 | €4"}',3.00,'',true,11,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Cappuccino"}','{"en": "Single | Double · €4 | €5"}',4.00,'',true,12,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Freddo Espresso"}','{"en": ""}',3.50,'',true,13,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Freddo Cappuccino"}','{"en": ""}',4.50,'',true,14,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Frappe"}','{"en": "& Ice Cream Frappe · €4 | €5"}',4.00,'',true,15,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Lipton Varius Flavors"}','{"en": ""}',4.00,'',true,16,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Cretan Herbal Tea"}','{"en": ""}',5.00,'',true,17,now(),now()) RETURNING id INTO v_item;
  END IF;
  -- COHILIA (get-or-create outlet)
  SELECT id INTO v_outlet FROM piato_outlet WHERE hotel_id=v_hotel AND name='Cohilia' ORDER BY id LIMIT 1;
  IF v_outlet IS NULL THEN
    INSERT INTO piato_outlet (hotel_id,name,otype,hours,qr_token,preview_token,published,sort,created_at,updated_at)
    VALUES (v_hotel,'Cohilia','pool_bar','10:00 — 18:00',md5(random()::text||clock_timestamp()::text),md5(random()::text||clock_timestamp()::text||'p'),false,1,now(),now()) RETURNING id INTO v_outlet;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Omeletes"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Omeletes"}','',true,1,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Simple"}','{"en": "Cured ham, cheese"}',6.50,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Special"}','{"en": "Cheese, Ham, Bacon, Sausage, Peppers, Onion"}',8.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Vegetarian"}','{"en": "Peppers, Onion, Tomatoes, Olives, Mushroom"}',8.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Pizzas"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Pizzas"}','',true,2,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Margarita"}','{"en": "Mozzarella, Tomato sauce"}',8.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Simple"}','{"en": "Mozzarella, Tomato sauce, Cured ham"}',8.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Mediterranean"}','{"en": "Mozzarella, Tomato sauce, Onion, Olives, Feta cheese"}',9.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Special"}','{"en": "Mozzarella, Tomato sauce, Pepperoni, Ham, Bacon, Peppers, Onion"}',10.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Salads"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Salads"}','',true,3,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Mixed Green"}','{"en": "Lettuce, Cherry tomatoes, Extra virgin olive vinaigrette"}',7.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Greek"}','{"en": "Tomatoes, Cucumber, Peppers, Onion, Lettuce, Olives, Feta cheese"}',7.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Tuna"}','{"en": "Tuna fillets, Onion, Lettuce, Edam cheese, Egg, Cocktail sauce"}',9.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','fish','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Caesar"}','{"en": "Lettuce, Cheese, Grilled Chicken, Tomatoes, Bacon, Crouton, Caesar sauce"}',10.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Toast – Baquettes – Tortillas"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Toast – Baquettes – Tortillas"}','',true,4,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Clasic Toast"}','{"en": "Ham and Cheese"}',4.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Turkey"}','{"en": "Turkey and Cheese"}',4.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "B.L.T. Baquette"}','{"en": "Smoked Bacon, Lettuce, Tomato, Mayo"}',6.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Traditional Baquette"}','{"en": "Lettuce, Tomato, Onion, Cucumber, Feta cheese, Peppers"}',7.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Chicken Baquette"}','{"en": "Grilled Chicken, Bacon, Cheese, Tomatoes, Bbq Sauce"}',10.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Tuna Tortilla"}','{"en": "Tuna fillets, Onion, Lettuce, Edam cheese, Mayo"}',8.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','fish','gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Chicken Tortilla"}','{"en": "Lettuce, Cheese, Grilled Chicken, Tomatoes, Caesar sauce"}',9.00,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Club Sandwich"}','{"en": "Lettuce, Cheese, Ham, Tomatoes, Bacon, Mayo"}',10.00,'',true,8,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Chicken Club"}','{"en": "Lettuce, Cheese, Ham, Grilled Chicken, Tomatoes, Bacon, Mayo"}',11.00,'',true,9,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Burgers"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Burgers"}','',true,5,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Hamburger"}','{"en": "Beef patty, Lettuce, Tomato, Onion, Mustard, Ketchup"}',7.50,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','mustard');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Cheeseburger"}','{"en": "Beef patty, Cheese, Lettuce, Tomato, Onion, Cocktail sauce"}',8.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Texas"}','{"en": "Beef patty, Lettuce, Tomato, Double Bacon, Onion, Bbq Sauce"}',8.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Chicken Burger"}','{"en": "Crispy Chicken, Bacon, Cheese, Tomatoes, Caesar sauce"}',9.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Greek Burger"}','{"en": "Lettuce, Crispy Chicken, Tomatoes, Tzatziki Sauce"}',9.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Meals & Sides"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "Meals & Sides"}','',true,6,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Grilled Chicken Fillet"}','{"en": "Chips on the side"}',12.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Chicken Nuggets"}','{"en": "Chips and salad on the side"}',9.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Pork Gyros"}','{"en": "Pita bread, Chips, Tomato, Onion, Yogurt"}',10.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Tzatziki"}','{"en": "Pita bread on the side"}',5.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "French Fries"}','{"en": ""}',5.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Dirty Fries"}','{"en": "Cheddar Cheese, and bacon"}',6.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "For Our Little Friends"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
    VALUES (v_outlet,'{"en": "For Our Little Friends"}','',true,7,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Chicken Nuggets"}','{"en": ""}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Fish Fingers"}','{"en": ""}',6.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('fish','gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Junior Hamburger"}','{"en": ""}',7.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Junior Cheeseburger"}','{"en": ""}',7.50,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
    VALUES (v_cat,'{"en": "Junior Chicken Burger"}','{"en": ""}',7.50,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
  END IF;
  RAISE NOTICE 'OK: Cohilia + Oliva drinks φορτώθηκαν (DRAFT).';
END $$;