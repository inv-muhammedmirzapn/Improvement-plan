import React from 'react';
import { SlidersHorizontal } from 'lucide-react';

export default function CategoryFilter({
  categories,
  selectedCategory,
  onSelectCategory,
  sortBy,
  onSortChange,
  totalResults,
}) {
  return (
    <div className="filter-bar">
      <div className="category-pills">
        {categories.map((cat) => (
          <button
            key={cat}
            className={`category-pill ${selectedCategory === cat ? 'active' : ''}`}
            onClick={() => onSelectCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="sort-section">
        <SlidersHorizontal size={15} />
        <span>Sort by:</span>
        <select
          className="sort-select"
          value={sortBy}
          onChange={(e) => onSortChange(e.target.value)}
        >
          <option value="default">Default</option>
          <option value="price-asc">Price: Low to High</option>
          <option value="price-desc">Price: High to Low</option>
          <option value="rating-desc">Highest Rated</option>
          <option value="title-asc">Name: A to Z</option>
        </select>
        <span style={{ marginLeft: 8, fontSize: '0.8rem', color: '#94a3b8' }}>
          ({totalResults} items)
        </span>
      </div>
    </div>
  );
}
