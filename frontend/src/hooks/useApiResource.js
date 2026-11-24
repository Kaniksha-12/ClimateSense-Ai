import { useEffect, useState } from 'react'

function useApiResource(request) {
  const [attempt, setAttempt] = useState(0)
  const [resource, setResource] = useState({ status: 'loading', data: null })

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    setResource({ status: 'loading', data: null })

    request({ signal: controller.signal })
      .then((data) => {
        if (active) setResource({ status: 'success', data })
      })
      .catch(() => {
        if (active) setResource({ status: 'error', data: null })
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [request, attempt])

  return {
    ...resource,
    retry: () => setAttempt((current) => current + 1),
  }
}

export default useApiResource
