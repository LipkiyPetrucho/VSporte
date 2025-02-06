from django.contrib.auth.models import User
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import TextField
from django.db.models.functions import Cast


def search_users(query):
    """Searches for users by first name, last name or login (case insensitive)
    using trigrams.
    Returns users by partial match with the query.
    """
    username_cast = Cast("username", TextField())
    first_name_cast = Cast("first_name", TextField())
    last_name_cast = Cast("last_name", TextField())

    search_query = (
        TrigramSimilarity(username_cast, query)
        + TrigramSimilarity(first_name_cast, query)
        + TrigramSimilarity(last_name_cast, query)
    )

    results = (
        User.objects.annotate(similarity=search_query)
        .filter(similarity__gt=0.1)
        .order_by("-similarity")
    )
    return results
