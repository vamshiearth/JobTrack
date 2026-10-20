interface Props {
  page: number
  totalPages: number
  total: number
  pageSize: number
  onPageChange: (page: number) => void
}

export default function ApplicationPagination({
  page,
  totalPages,
  total,
  pageSize,
  onPageChange,
}: Props) {
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)
  return (
    <nav className='applications-pagination' aria-label='Application pages'>
      <span>
        Showing {start}-{end} of {total}
      </span>
      <div className='pagination-buttons'>
        <button
          type='button'
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        <span>
          Page {page} of {totalPages}
        </span>
        <button
          type='button'
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </nav>
  )
}
