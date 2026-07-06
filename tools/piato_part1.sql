-- PIATO 1/3 - Oliva drinks A (aperitifs..rose)
DO $$
DECLARE v_hotel int; v_outlet int; v_cat int; v_item int;
BEGIN
  SELECT id INTO v_hotel FROM hotel WHERE name ILIKE '%asterias%' ORDER BY id LIMIT 1;
  IF v_hotel IS NULL THEN RAISE EXCEPTION 'Asterias not found'; END IF;
  SELECT id INTO v_outlet FROM piato_outlet WHERE hotel_id=v_hotel AND name ILIKE '%oliva%' ORDER BY id LIMIT 1;
  IF v_outlet IS NULL THEN RAISE EXCEPTION 'Oliva not found'; END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Aperitifs"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Aperitifs"}','',true,10,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Raki Shot | Carafe 120ml"}','{"en": "€2 | €6"}',2.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Ouzo Glass | Bottle 200ml"}','{"en": "€4.5 | €14"}',4.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Martini Bianco"}','{"en": ""}',5.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Martini Dry"}','{"en": ""}',5.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Campari"}','{"en": ""}',5.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Aperol"}','{"en": ""}',5.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Sparkling"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Sparkling"}','',true,11,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Prosecco Glass | Bottle"}','{"en": "€6 | €30"}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Moscato D’ Asti Glass | Bottle"}','{"en": "€6 | €30"}',6.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Aperol Spritz"}','{"en": ""}',8.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Kir Royal"}','{"en": ""}',8.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Mimosa"}','{"en": ""}',8.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Beers"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Beers"}','',true,12,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Amstel free 330 0%"}','{"en": ""}',4.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Draft Mythos 300 5%"}','{"en": ""}',4.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Draft Mythos 500 5%"}','{"en": ""}',5.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Mythos 330 5%"}','{"en": ""}',4.50,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Amstel 330 5%"}','{"en": ""}',4.50,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Heineken 3305%"}','{"en": ""}',4.50,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Erdinger Weiss 500 5.3 %"}','{"en": ""}',8.00,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "White Wine"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "White Wine"}','',true,13,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "House Lyrarakis 2024"}','{"en": "Glass | Carafe 500ml | Carafe 1L · €5 | €8 | €14"}',5.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Savignon Blanc Local Cretan 2025"}','{"en": "Glass | Bottle · €5 | €30"}',5.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Marmaromenos Vasilias Asyrtiko 2024"}','{"en": "Glass | Bottle · €6 | €35"}',6.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Little Angel Thrapsathiri Vidiano Awarded of Crete"}','{"en": "€7 | €40"}',7.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Plyto Rare Local Crete Fruity Variety 2025"}','{"en": "€8 | €45"}',8.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Asyrtiko Terra Divino Awarded of Crete 2025"}','{"en": "€9 | €50"}',9.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Chardonnay Terra Divino Winery of Crete 2025"}','{"en": "€9 | €50"}',9.00,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Red Wine"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Red Wine"}','',true,14,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "House Lyrarakis 2024"}','{"en": "Glass | Carafe 500ml | Carafe 1L · €5 | €8 | €14"}',5.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Merlot Terra Divino Winery of Crete 2024"}','{"en": "€5 | €30"}',5.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Little Angel Kotsifali Cabernet Sauvignon 24"}','{"en": "Glass | Bottle · €7 | €40"}',7.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Portes Skoyras Merlot 2023"}','{"en": "Glass | Bottle · €7 | €40"}',7.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Rose"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Rose"}','',true,15,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "House Lyrarakis 2024"}','{"en": "Glass | Carafe 500ml | Carafe 1L · €5 | €8 | €14"}',5.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Dafnios Vidiano 2025"}','{"en": "Glass | Bottle · €6 | €35"}',6.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Maskes Merlot 2023"}','{"en": "Glass | Bottle · €8 | €45"}',8.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Peplo Syrah 2023"}','{"en": "Glass | Bottle · €9 | €50"}',9.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Little Angel Rose 2025 Liatiko -syrah Awarded Wine"}','{"en": "€9 | €50"}',9.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Sirines Rose 2025 Medium Dry Grenache Rouge Liatiko"}','{"en": "€9 | €50"}',9.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  END IF;
  RAISE NOTICE 'PIATO 1/3 - Oliva drinks A (aperitifs..rose) OK';
END $$;
