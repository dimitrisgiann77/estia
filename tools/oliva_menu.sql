-- Piato · Oliva A la carte Restaurant -> Asterias Village Resort (P-075)
-- Paste ΟΛΟΚΛΗΡΟ στο Railway → Postgres → Query. Τρέξε ΜΕΤΑ το deploy του Piato.
-- Idempotent (αν υπάρχει ήδη το outlet → καμία αλλαγή). Το μενού μπαίνει DRAFT.
DO $$
DECLARE v_hotel int; v_outlet int; v_cat int; v_item int;
BEGIN
  SELECT id INTO v_hotel FROM hotel WHERE name ILIKE '%asterias%' ORDER BY id LIMIT 1;
  IF v_hotel IS NULL THEN RAISE EXCEPTION 'Δεν βρέθηκε ξενοδοχείο (%)', 'asterias'; END IF;
  IF EXISTS (SELECT 1 FROM piato_outlet WHERE hotel_id=v_hotel AND name='Oliva A la carte Restaurant') THEN
     RAISE NOTICE 'Το outlet υπάρχει ήδη — καμία αλλαγή'; RETURN; END IF;
  INSERT INTO piato_outlet (hotel_id,name,otype,hours,qr_token,preview_token,published,sort,created_at,updated_at)
  VALUES (v_hotel,'Oliva A la carte Restaurant','restaurant','',md5(random()::text||clock_timestamp()::text),md5(random()::text||clock_timestamp()::text||'p'),false,0,now(),now())
  RETURNING id INTO v_outlet;
  -- Appetizers
  INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
  VALUES (v_outlet,'{"en": "Appetizers"}','',true,1,now(),now()) RETURNING id INTO v_cat;
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Tzatziki"}','{"en": "Accompanied with mini rusks"}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk','gluten');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Ntolmadakia"}','{"en": "Cretan grape leaves stuffed with rice"}',7.00,'',true,2,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Dakos"}','{"en": "Cretan rusk with olive oil, tomato and crumbled feta cheese"}',6.50,'',true,3,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Flutes"}','{"en": "Cured ham, kasseri cheese and sweet chili dip"}',6.00,'',true,4,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Fried Squid"}','{"en": "Accompanied with a splash of tzatziki"}',7.00,'',true,5,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('molluscs','gluten','milk');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Mussels & Shrimps Saganaki"}','{"en": "Mussels, shrimps, vegetables, tomato sauce, garlic and ouzo"}',9.50,'',true,6,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('molluscs','crustaceans');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Stuffed Potato"}','{"en": "With selected vegetables & chilly sauce"}',6.00,'',true,7,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "French Fries"}','{}',5.00,'',true,8,now(),now()) RETURNING id INTO v_item;
  -- Salads
  INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
  VALUES (v_outlet,'{"en": "Salads"}','',true,2,now(),now()) RETURNING id INTO v_cat;
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Mixed Green Salad"}','{"en": "Green leaves, mature balsamic vinaigrette"}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Greek Salad"}','{"en": "Tomatoes, cucumber, onions, green peppers, olives and feta"}',7.20,'',true,2,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Cretan Salad"}','{"en": "Cherry tomatoes, cucumber, onions, green peppers, olives, eggs, potatoes, rusk"}',8.50,'',true,3,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','eggs');
  -- Main Courses
  INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
  VALUES (v_outlet,'{"en": "Main Courses"}','',true,3,now(),now()) RETURNING id INTO v_cat;
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Skioufichta"}','{"en": "Cretan fresh pasta with tomato sauce and vegetables"}',8.90,'',true,1,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Cretan Ravioli"}','{}',10.50,'',true,2,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Braised Beef"}','{"en": "With mashed potatoes"}',15.50,'',true,3,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Grilled Chicken Fillet"}','{"en": "With grilled vegetables and balsamic vinegar cream"}',13.50,'',true,4,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Pork Chop"}','{"en": "With fried potatoes and pepper sauce"}',13.50,'',true,5,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Chicken Souvlaki"}','{}',12.50,'',true,6,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Pork Souvlaki"}','{}',12.50,'',true,7,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Grilled Perch"}','{}',12.80,'',true,8,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('fish');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Sea Bream"}','{}',20.00,'',true,9,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('fish');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Mix Grill"}','{"en": "For 2"}',35.50,'',true,10,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Lamb Chops"}','{}',27.00,'',true,11,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Grilled Burgers"}','{"en": "With mashed potatoes"}',14.50,'',true,12,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Pork Belly"}','{"en": "With BBQ sauce"}',13.50,'',true,13,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Spaghetti Bolognese"}','{"en": "With minced meat of pork and beef"}',10.00,'',true,14,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Stable Pork Steak (800-900gr)"}','{}',25.00,'',true,15,now(),now()) RETURNING id INTO v_item;
  -- Desserts
  INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)
  VALUES (v_outlet,'{"en": "Desserts"}','',true,4,now(),now()) RETURNING id INTO v_cat;
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Chocolate Fudge"}','{}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk','eggs');
  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)
  VALUES (v_cat,'{"en": "Ice Cream"}','{"en": "2 scoops of your choice: vanilla, chocolate and strawberry"}',4.00,'',true,2,now(),now()) RETURNING id INTO v_item;
  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
  RAISE NOTICE 'OK: Oliva φορτώθηκε (DRAFT). Έλεγξε αλλεργιογόνα & δημοσίευσε από την κονσόλα.';
END $$;
