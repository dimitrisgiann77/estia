-- Piato · Oliva (EL+EN) -> Asterias Village Resort (P-075). Paste ΟΛΟΚΛΗΡΟ στο Railway Query.
-- Idempotent UPSERT: εισάγει νέα, ΕΝΗΜΕΡΩΝΕΙ τίτλους/περιγραφές σε υπάρχοντα. Μπαίνει DRAFT.
DO $$
DECLARE v_hotel int; v_outlet int; v_cat int; v_item int;
BEGIN
  SELECT id INTO v_hotel FROM hotel WHERE name ILIKE '%asterias%' ORDER BY id LIMIT 1;
  IF v_hotel IS NULL THEN RAISE EXCEPTION 'Δεν βρέθηκε ξενοδοχείο'; END IF;
  SELECT id INTO v_outlet FROM piato_outlet WHERE hotel_id=v_hotel AND name='Oliva A la carte Restaurant' LIMIT 1;
  IF v_outlet IS NULL THEN
    INSERT INTO piato_outlet (hotel_id,name,otype,hours,qr_token,preview_token,published,sort,created_at,updated_at)
    VALUES (v_hotel,'Oliva A la carte Restaurant','restaurant','',md5(random()::text||clock_timestamp()::text),md5(random()::text||clock_timestamp()::text||'p'),false,0,now(),now()) RETURNING id INTO v_outlet;
  END IF;
  -- Appetizers / Ορεκτικά
  SELECT id INTO v_cat FROM piato_category WHERE outlet_id=v_outlet AND (name_i18n::jsonb->>'en')='Appetizers' LIMIT 1;
  IF v_cat IS NULL THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"el": "Ορεκτικά", "en": "Appetizers"}','',true,1,now(),now()) RETURNING id INTO v_cat;
  ELSE UPDATE piato_category SET name_i18n='{"el": "Ορεκτικά", "en": "Appetizers"}' WHERE id=v_cat; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Tzatziki' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Τζατζίκι", "en": "Tzatziki"}','{"el": "Συνοδεύεται με παξιμαδάκια", "en": "Accompanied with mini rusks"}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk','gluten');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Τζατζίκι", "en": "Tzatziki"}', desc_i18n='{"el": "Συνοδεύεται με παξιμαδάκια", "en": "Accompanied with mini rusks"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Ntolmadakia' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Ντολμαδάκια", "en": "Ntolmadakia"}','{"el": "Κρητικά αμπελόφυλλα γεμιστά με ρύζι", "en": "Cretan grape leaves stuffed with rice"}',7.00,'',true,2,now(),now()) RETURNING id INTO v_item;
  ELSE UPDATE piato_item SET title_i18n='{"el": "Ντολμαδάκια", "en": "Ntolmadakia"}', desc_i18n='{"el": "Κρητικά αμπελόφυλλα γεμιστά με ρύζι", "en": "Cretan grape leaves stuffed with rice"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Dakos' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Ντάκος", "en": "Dakos"}','{"el": "Κρητικό παξιμάδι με ελαιόλαδο, ντομάτα και θρυμματισμένη φέτα", "en": "Cretan rusk with olive oil, tomato and crumbled feta cheese"}',6.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Ντάκος", "en": "Dakos"}', desc_i18n='{"el": "Κρητικό παξιμάδι με ελαιόλαδο, ντομάτα και θρυμματισμένη φέτα", "en": "Cretan rusk with olive oil, tomato and crumbled feta cheese"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Flutes' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Φλογέρες", "en": "Flutes"}','{"el": "Ζαμπόν, κασέρι και ντιπ γλυκού τσίλι", "en": "Cured ham, kasseri cheese and sweet chili dip"}',6.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Φλογέρες", "en": "Flutes"}', desc_i18n='{"el": "Ζαμπόν, κασέρι και ντιπ γλυκού τσίλι", "en": "Cured ham, kasseri cheese and sweet chili dip"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Fried Squid' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Καλαμαράκια τηγανητά", "en": "Fried Squid"}','{"el": "Συνοδεύονται με λίγο τζατζίκι", "en": "Accompanied with a splash of tzatziki"}',7.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('molluscs','gluten','milk');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Καλαμαράκια τηγανητά", "en": "Fried Squid"}', desc_i18n='{"el": "Συνοδεύονται με λίγο τζατζίκι", "en": "Accompanied with a splash of tzatziki"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Mussels & Shrimps Saganaki' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Μύδια & Γαρίδες σαγανάκι", "en": "Mussels & Shrimps Saganaki"}','{"el": "Μύδια, γαρίδες, λαχανικά, σάλτσα ντομάτας, σκόρδο και ούζο", "en": "Mussels, shrimps, vegetables, tomato sauce, garlic and ouzo"}',9.50,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('molluscs','crustaceans');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Μύδια & Γαρίδες σαγανάκι", "en": "Mussels & Shrimps Saganaki"}', desc_i18n='{"el": "Μύδια, γαρίδες, λαχανικά, σάλτσα ντομάτας, σκόρδο και ούζο", "en": "Mussels, shrimps, vegetables, tomato sauce, garlic and ouzo"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Stuffed Potato' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Πατάτα γεμιστή", "en": "Stuffed Potato"}','{"el": "Με επιλεγμένα λαχανικά & σάλτσα τσίλι", "en": "With selected vegetables & chilly sauce"}',6.00,'',true,7,now(),now()) RETURNING id INTO v_item;
  ELSE UPDATE piato_item SET title_i18n='{"el": "Πατάτα γεμιστή", "en": "Stuffed Potato"}', desc_i18n='{"el": "Με επιλεγμένα λαχανικά & σάλτσα τσίλι", "en": "With selected vegetables & chilly sauce"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='French Fries' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Πατάτες τηγανητές", "en": "French Fries"}','{}',5.00,'',true,8,now(),now()) RETURNING id INTO v_item;
  ELSE UPDATE piato_item SET title_i18n='{"el": "Πατάτες τηγανητές", "en": "French Fries"}', desc_i18n='{}' WHERE id=v_item; END IF;
  -- Salads / Σαλάτες
  SELECT id INTO v_cat FROM piato_category WHERE outlet_id=v_outlet AND (name_i18n::jsonb->>'en')='Salads' LIMIT 1;
  IF v_cat IS NULL THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"el": "Σαλάτες", "en": "Salads"}','',true,2,now(),now()) RETURNING id INTO v_cat;
  ELSE UPDATE piato_category SET name_i18n='{"el": "Σαλάτες", "en": "Salads"}' WHERE id=v_cat; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Mixed Green Salad' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Πράσινη σαλάτα", "en": "Mixed Green Salad"}','{"el": "Πράσινα φύλλα, βινεγκρέτ ώριμου βαλσάμικου", "en": "Green leaves, mature balsamic vinaigrette"}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Πράσινη σαλάτα", "en": "Mixed Green Salad"}', desc_i18n='{"el": "Πράσινα φύλλα, βινεγκρέτ ώριμου βαλσάμικου", "en": "Green leaves, mature balsamic vinaigrette"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Greek Salad' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Χωριάτικη σαλάτα", "en": "Greek Salad"}','{"el": "Ντομάτα, αγγούρι, κρεμμύδι, πράσινη πιπεριά, ελιές και φέτα", "en": "Tomatoes, cucumber, onions, green peppers, olives and feta"}',7.20,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Χωριάτικη σαλάτα", "en": "Greek Salad"}', desc_i18n='{"el": "Ντομάτα, αγγούρι, κρεμμύδι, πράσινη πιπεριά, ελιές και φέτα", "en": "Tomatoes, cucumber, onions, green peppers, olives and feta"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Cretan Salad' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Κρητική σαλάτα", "en": "Cretan Salad"}','{"el": "Ντοματίνια, αγγούρι, κρεμμύδι, πράσινη πιπεριά, ελιές, αυγό, πατάτα, παξιμάδι", "en": "Cherry tomatoes, cucumber, onions, green peppers, olives, eggs, potatoes, rusk"}',8.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','eggs');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Κρητική σαλάτα", "en": "Cretan Salad"}', desc_i18n='{"el": "Ντοματίνια, αγγούρι, κρεμμύδι, πράσινη πιπεριά, ελιές, αυγό, πατάτα, παξιμάδι", "en": "Cherry tomatoes, cucumber, onions, green peppers, olives, eggs, potatoes, rusk"}' WHERE id=v_item; END IF;
  -- Main Courses / Κυρίως Πιάτα
  SELECT id INTO v_cat FROM piato_category WHERE outlet_id=v_outlet AND (name_i18n::jsonb->>'en')='Main Courses' LIMIT 1;
  IF v_cat IS NULL THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"el": "Κυρίως Πιάτα", "en": "Main Courses"}','',true,3,now(),now()) RETURNING id INTO v_cat;
  ELSE UPDATE piato_category SET name_i18n='{"el": "Κυρίως Πιάτα", "en": "Main Courses"}' WHERE id=v_cat; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Skioufichta' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Σκιουφιχτά", "en": "Skioufichta"}','{"el": "Κρητικά χειροποίητα ζυμαρικά με σάλτσα ντομάτας και λαχανικά", "en": "Cretan fresh pasta with tomato sauce and vegetables"}',8.90,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Σκιουφιχτά", "en": "Skioufichta"}', desc_i18n='{"el": "Κρητικά χειροποίητα ζυμαρικά με σάλτσα ντομάτας και λαχανικά", "en": "Cretan fresh pasta with tomato sauce and vegetables"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Cretan Ravioli' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Κρητικά ραβιόλια", "en": "Cretan Ravioli"}','{}',10.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Κρητικά ραβιόλια", "en": "Cretan Ravioli"}', desc_i18n='{}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Braised Beef' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Μοσχάρι κοκκινιστό", "en": "Braised Beef"}','{"el": "Με πουρέ πατάτας", "en": "With mashed potatoes"}',15.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Μοσχάρι κοκκινιστό", "en": "Braised Beef"}', desc_i18n='{"el": "Με πουρέ πατάτας", "en": "With mashed potatoes"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Grilled Chicken Fillet' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Φιλέτο κοτόπουλο σχάρας", "en": "Grilled Chicken Fillet"}','{"el": "Με λαχανικά σχάρας και κρέμα βαλσάμικου", "en": "With grilled vegetables and balsamic vinegar cream"}',13.50,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Φιλέτο κοτόπουλο σχάρας", "en": "Grilled Chicken Fillet"}', desc_i18n='{"el": "Με λαχανικά σχάρας και κρέμα βαλσάμικου", "en": "With grilled vegetables and balsamic vinegar cream"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Pork Chop' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Χοιρινή μπριζόλα", "en": "Pork Chop"}','{"el": "Με τηγανητές πατάτες και σάλτσα πιπεριού", "en": "With fried potatoes and pepper sauce"}',13.50,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Χοιρινή μπριζόλα", "en": "Pork Chop"}', desc_i18n='{"el": "Με τηγανητές πατάτες και σάλτσα πιπεριού", "en": "With fried potatoes and pepper sauce"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Chicken Souvlaki' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Κοτόπουλο σουβλάκι", "en": "Chicken Souvlaki"}','{}',12.50,'',true,6,now(),now()) RETURNING id INTO v_item;
  ELSE UPDATE piato_item SET title_i18n='{"el": "Κοτόπουλο σουβλάκι", "en": "Chicken Souvlaki"}', desc_i18n='{}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Pork Souvlaki' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Χοιρινό σουβλάκι", "en": "Pork Souvlaki"}','{}',12.50,'',true,7,now(),now()) RETURNING id INTO v_item;
  ELSE UPDATE piato_item SET title_i18n='{"el": "Χοιρινό σουβλάκι", "en": "Pork Souvlaki"}', desc_i18n='{}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Grilled Perch' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Πέρκα σχάρας", "en": "Grilled Perch"}','{}',12.80,'',true,8,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('fish');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Πέρκα σχάρας", "en": "Grilled Perch"}', desc_i18n='{}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Sea Bream' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Τσιπούρα", "en": "Sea Bream"}','{}',20.00,'',true,9,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('fish');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Τσιπούρα", "en": "Sea Bream"}', desc_i18n='{}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Mix Grill' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Μιξ γκριλ", "en": "Mix Grill"}','{"el": "Για 2 άτομα", "en": "For 2"}',35.50,'',true,10,now(),now()) RETURNING id INTO v_item;
  ELSE UPDATE piato_item SET title_i18n='{"el": "Μιξ γκριλ", "en": "Mix Grill"}', desc_i18n='{"el": "Για 2 άτομα", "en": "For 2"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Lamb Chops' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Αρνίσια παϊδάκια", "en": "Lamb Chops"}','{}',27.00,'',true,11,now(),now()) RETURNING id INTO v_item;
  ELSE UPDATE piato_item SET title_i18n='{"el": "Αρνίσια παϊδάκια", "en": "Lamb Chops"}', desc_i18n='{}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Grilled Burgers' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Μπιφτέκια σχάρας", "en": "Grilled Burgers"}','{"el": "Με πουρέ πατάτας", "en": "With mashed potatoes"}',14.50,'',true,12,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Μπιφτέκια σχάρας", "en": "Grilled Burgers"}', desc_i18n='{"el": "Με πουρέ πατάτας", "en": "With mashed potatoes"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Pork Belly' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Χοιρινή πανσέτα", "en": "Pork Belly"}','{"el": "Με σάλτσα BBQ", "en": "With BBQ sauce"}',13.50,'',true,13,now(),now()) RETURNING id INTO v_item;
  ELSE UPDATE piato_item SET title_i18n='{"el": "Χοιρινή πανσέτα", "en": "Pork Belly"}', desc_i18n='{"el": "Με σάλτσα BBQ", "en": "With BBQ sauce"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Spaghetti Bolognese' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Σπαγγέτι μπολονέζ", "en": "Spaghetti Bolognese"}','{"el": "Με κιμά χοιρινό και μοσχαρίσιο", "en": "With minced meat of pork and beef"}',10.00,'',true,14,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Σπαγγέτι μπολονέζ", "en": "Spaghetti Bolognese"}', desc_i18n='{"el": "Με κιμά χοιρινό και μοσχαρίσιο", "en": "With minced meat of pork and beef"}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Stable Pork Steak (800-900gr)' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Χοιρινή μπριζόλα (800-900γρ.)", "en": "Stable Pork Steak (800-900gr)"}','{}',25.00,'',true,15,now(),now()) RETURNING id INTO v_item;
  ELSE UPDATE piato_item SET title_i18n='{"el": "Χοιρινή μπριζόλα (800-900γρ.)", "en": "Stable Pork Steak (800-900gr)"}', desc_i18n='{}' WHERE id=v_item; END IF;
  -- Desserts / Επιδόρπια
  SELECT id INTO v_cat FROM piato_category WHERE outlet_id=v_outlet AND (name_i18n::jsonb->>'en')='Desserts' LIMIT 1;
  IF v_cat IS NULL THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"el": "Επιδόρπια", "en": "Desserts"}','',true,4,now(),now()) RETURNING id INTO v_cat;
  ELSE UPDATE piato_category SET name_i18n='{"el": "Επιδόρπια", "en": "Desserts"}' WHERE id=v_cat; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Chocolate Fudge' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Σοκολατόπιτα", "en": "Chocolate Fudge"}','{}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk','eggs');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Σοκολατόπιτα", "en": "Chocolate Fudge"}', desc_i18n='{}' WHERE id=v_item; END IF;
  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='Ice Cream' LIMIT 1;
  IF v_item IS NULL THEN
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"el": "Παγωτό", "en": "Ice Cream"}','{"el": "2 μπάλες της επιλογής σας: βανίλια, σοκολάτα, φράουλα", "en": "2 scoops of your choice: vanilla, chocolate and strawberry"}',4.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
  ELSE UPDATE piato_item SET title_i18n='{"el": "Παγωτό", "en": "Ice Cream"}', desc_i18n='{"el": "2 μπάλες της επιλογής σας: βανίλια, σοκολάτα, φράουλα", "en": "2 scoops of your choice: vanilla, chocolate and strawberry"}' WHERE id=v_item; END IF;
  RAISE NOTICE 'OK: Oliva (EL+EN) φορτώθηκε/ενημερώθηκε (DRAFT).';
END $$;
