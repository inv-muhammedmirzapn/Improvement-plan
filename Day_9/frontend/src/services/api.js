/**
 * API service for communicating with the Django REST Framework backend.
 */

export async function fetchProducts({ category, search, ordering } = {}) {
  const params = new URLSearchParams();
  if (category && category !== 'All') params.append('category', category);
  if (search) params.append('search', search);
  if (ordering) params.append('ordering', ordering);

  const queryStr = params.toString() ? `?${params.toString()}` : '';

  const res = await fetch(`/api/products/${queryStr}`, {
    headers: { Accept: 'application/json' },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch products: ${res.status} ${res.statusText}`);
  }

  const data = await res.json();
  return { data };
}

export async function fetchCategories() {
  const res = await fetch('/api/categories/', {
    headers: { Accept: 'application/json' },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch categories: ${res.status} ${res.statusText}`);
  }

  const data = await res.json();
  return ['All', ...data];
}
