interface StatCardProps {
  title: string
  value: number
  icon: string
  description: string
}

export default function StatCard({
  title,
  value,
  icon,
  description,
}: StatCardProps) {
  return (
    <article className='stat-card'>
      <div className='stat-card-top'>
        <span className='stat-icon' aria-hidden='true'>
          {icon}
        </span>
      </div>
      <strong className='stat-value'>{value.toLocaleString()}</strong>
      <h3>{title}</h3>
      <p>{description}</p>
    </article>
  )
}
