interface SubmissionConfirmationProps {
  disabled: boolean
  onConfirm: () => void
}

export default function SubmissionConfirmation({
  disabled,
  onConfirm,
}: SubmissionConfirmationProps) {
  return (
    <button
      type='button'
      className='primary-button'
      disabled={disabled}
      onClick={onConfirm}
    >
      Confirm submission
    </button>
  )
}
