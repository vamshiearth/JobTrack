import { useEffect, useState } from 'react'
import {
  getCandidateProfile,
  saveCandidateProfile,
  type CandidateProfileInput,
} from '../../api/candidateProfile'

interface Props {
  csrfToken: string
}

const emptyProfile: CandidateProfileInput = {
  skills: [],
  experience_summary: '',
  target_roles: [],
  preferred_locations: [],
  remote_preference: null,
  resume_version: 'qa-profile-1',
}

function splitValues(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export default function CandidateProfileEditor({ csrfToken }: Props) {
  const [profile, setProfile] = useState<CandidateProfileInput>(emptyProfile)
  const [skills, setSkills] = useState('')
  const [roles, setRoles] = useState('')
  const [locations, setLocations] = useState('')
  const [status, setStatus] = useState('Loading profile...')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    void getCandidateProfile()
      .then((loaded) => {
        const next = {
          skills: loaded.skills,
          experience_summary: loaded.experience_summary,
          target_roles: loaded.target_roles,
          preferred_locations: loaded.preferred_locations,
          remote_preference: loaded.remote_preference,
          resume_version: loaded.resume_version,
        }
        setProfile(next)
        setSkills(loaded.skills.join(', '))
        setRoles(loaded.target_roles.join(', '))
        setLocations(loaded.preferred_locations.join(', '))
        setStatus(`Confirmed profile revision ${loaded.revision}`)
      })
      .catch(() => setStatus('No confirmed profile yet'))
  }, [])

  async function save() {
    setSaving(true)
    setStatus('Saving confirmed profile...')
    const next = {
      ...profile,
      skills: splitValues(skills),
      target_roles: splitValues(roles),
      preferred_locations: splitValues(locations),
    }
    try {
      const saved = await saveCandidateProfile(next, csrfToken)
      setProfile(next)
      setStatus(`Confirmed profile revision ${saved.revision}`)
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : 'Could not save profile',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className='settings-panel'>
      <h3>Candidate profile</h3>
      <p>Only saved values are used as confirmed ranking evidence.</p>
      <label>
        Confirmed skills
        <input
          value={skills}
          onChange={(event) => setSkills(event.target.value)}
          placeholder='Oracle CPQ, Java, Spring Boot, REST APIs'
        />
      </label>
      <label>
        Target roles
        <input
          value={roles}
          onChange={(event) => setRoles(event.target.value)}
          placeholder='Oracle CPQ Developer, Java Backend Engineer'
        />
      </label>
      <label>
        Preferred locations
        <input
          value={locations}
          onChange={(event) => setLocations(event.target.value)}
          placeholder='Boston, MA, United States Remote'
        />
      </label>
      <label>
        Remote preference
        <select
          value={profile.remote_preference ?? ''}
          onChange={(event) =>
            setProfile({
              ...profile,
              remote_preference: event.target.value || null,
            })
          }
        >
          <option value=''>No preference</option>
          <option value='REMOTE'>Remote</option>
          <option value='HYBRID'>Hybrid</option>
          <option value='ONSITE'>Onsite</option>
        </select>
      </label>
      <label>
        Experience evidence
        <textarea
          value={profile.experience_summary ?? ''}
          onChange={(event) =>
            setProfile({ ...profile, experience_summary: event.target.value })
          }
          rows={4}
        />
      </label>
      <label>
        Resume version
        <input
          value={profile.resume_version}
          onChange={(event) =>
            setProfile({ ...profile, resume_version: event.target.value })
          }
        />
      </label>
      <button
        type='button'
        onClick={() => void save()}
        disabled={saving || !csrfToken || !profile.resume_version.trim()}
      >
        {saving ? 'Saving...' : 'Save confirmed profile'}
      </button>
      <p role='status'>{status}</p>
    </div>
  )
}
