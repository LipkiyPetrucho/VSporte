from games.views import r
from .models import Place


class Recommender:
    def get_place_key(self, id):
        return f"place:{id}:purchased_with"

    def places_bought(self, places):
        place_ids = [p.id for p in places]
        for place_id in place_ids:
            for with_id in place_ids:
                # получить другие товары, купленные вместе с каждым товаром
                if place_id != with_id:
                    # увеличить балл товара,
                    # купленного вместе
                    r.zincrby(self.get_place_key(place_id), 1, with_id)

    def suggest_places_for(self, places, max_results=6):
        place_ids = [p.id for p in places]
        if len(places) == 1:
            # только 1 товар
            suggestions = r.zrange(self.get_place_key(place_ids[0]), 0, -1, desc=True)[
                :max_results
            ]

        else:
            # сгенерировать временный ключ
            flat_ids = "".join([str(id) for id in place_ids])
            tmp_key = f"tmp_{flat_ids}"
            # несколько товаров, объединить баллы всех товаров
            # сохранить полученное сортированное множество
            # во временном ключе
            keys = [self.get_place_key(id) for id in place_ids]
            r.zunionstore(tmp_key, keys)
            # удалить идентификаторы товаров,
            # для которых дается рекомендация
            r.zrem(tmp_key, *place_ids)
            # получить идентификаторы товаров по их количеству,
            # сортировка по убыванию
            suggestions = r.zrange(tmp_key, 0, -1, desc=True)[:max_results]
            # удалить временный ключ
            r.delete(tmp_key)
        suggested_places_ids = [int(id) for id in suggestions]
        # получить предлагаемые товары и
        # отсортировать их по порядку их появления
        suggested_places = list(Place.objects.filter(id__in=suggested_places_ids))
        suggested_places.sort(key=lambda x: suggested_places_ids.index(x.id))
        return suggested_places

    def clear_purchases(self):
        for id in Place.objects.values_list("id", flat=True):
            r.delete(self.get_place_key(id))
