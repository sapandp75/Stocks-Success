import { createContext, useContext, useState, useEffect } from 'react'
import { getRegime } from './api'

const RegimeContext = createContext(null)

export function RegimeProvider({ children }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refresh = () => {
    setLoading(true)
    setError(null)
    getRegime()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { refresh() }, [])

  return (
    <RegimeContext.Provider value={{ data, loading, error, refresh }}>
      {children}
    </RegimeContext.Provider>
  )
}

export function useRegime() {
  return useContext(RegimeContext)
}
