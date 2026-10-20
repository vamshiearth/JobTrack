import type {
  ApplicationFilters,
  TrackedApplication,
} from '../types/application'

export interface ApplicationPage {
  items: TrackedApplication[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export function filterApplications(
  applications: TrackedApplication[],
  filters: ApplicationFilters,
): ApplicationPage {
  const query = filters.q.trim().toLocaleLowerCase()
  const filtered = applications.filter((application) => {
    const matchesQuery =
      !query ||
      application.companyName.toLocaleLowerCase().includes(query) ||
      application.jobTitle.toLocaleLowerCase().includes(query)
    const matchesStage =
      filters.stage === 'ALL' || application.stage === filters.stage
    const matchesOwner =
      filters.nextActionOwner === 'ALL' ||
      application.nextActionOwner === filters.nextActionOwner
    return matchesQuery && matchesStage && matchesOwner
  })

  const sorted = [...filtered].sort((a, b) => {
    const aValue =
      filters.sortBy === 'company_name'
        ? a.companyName.toLocaleLowerCase()
        : filters.sortBy === 'applied_at'
          ? a.appliedAt
          : a.lastActivityAt
    const bValue =
      filters.sortBy === 'company_name'
        ? b.companyName.toLocaleLowerCase()
        : filters.sortBy === 'applied_at'
          ? b.appliedAt
          : b.lastActivityAt
    const comparison = aValue.localeCompare(bValue)
    return comparison !== 0
      ? filters.sortOrder === 'asc'
        ? comparison
        : -comparison
      : a.id.localeCompare(b.id)
  })

  const total = sorted.length
  const totalPages = Math.max(1, Math.ceil(total / filters.pageSize))
  const page = Math.min(Math.max(1, filters.page), totalPages)
  const offset = (page - 1) * filters.pageSize

  return {
    items: sorted.slice(offset, offset + filters.pageSize),
    total,
    page,
    pageSize: filters.pageSize,
    totalPages,
  }
}
