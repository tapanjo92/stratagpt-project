'use client'

import { useAuth } from '@/contexts/AuthContext'
import { Menu, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import { UserCircleIcon, ArrowRightOnRectangleIcon, DocumentTextIcon } from '@heroicons/react/24/outline'

export default function Header() {
  const { user, signOut } = useAuth()

  if (!user) return null

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <DocumentTextIcon className="w-8 h-8 text-strata-600 mr-3" />
            <h1 className="text-xl font-semibold text-gray-900">
              Australian Strata GPT
            </h1>
          </div>

          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">
              Tenant: <span className="font-medium">{user.tenantId}</span>
            </span>

            <Menu as="div" className="relative">
              <Menu.Button className="flex items-center space-x-2 text-gray-700 hover:text-gray-900">
                <UserCircleIcon className="w-8 h-8" />
                <span className="text-sm font-medium">{user.email}</span>
              </Menu.Button>

              <Transition
                as={Fragment}
                enter="transition ease-out duration-100"
                enterFrom="transform opacity-0 scale-95"
                enterTo="transform opacity-100 scale-100"
                leave="transition ease-in duration-75"
                leaveFrom="transform opacity-100 scale-100"
                leaveTo="transform opacity-0 scale-95"
              >
                <Menu.Items className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-1 z-50">
                  <Menu.Item>
                    {({ active }) => (
                      <div className="px-4 py-2 border-b border-gray-100">
                        <p className="text-sm font-medium text-gray-900">{user.email}</p>
                        <p className="text-xs text-gray-500 capitalize">{user.role}</p>
                      </div>
                    )}
                  </Menu.Item>
                  
                  <Menu.Item>
                    {({ active }) => (
                      <button
                        onClick={() => signOut()}
                        className={`${
                          active ? 'bg-gray-100' : ''
                        } flex items-center w-full px-4 py-2 text-sm text-gray-700`}
                      >
                        <ArrowRightOnRectangleIcon className="w-4 h-4 mr-2" />
                        Sign Out
                      </button>
                    )}
                  </Menu.Item>
                </Menu.Items>
              </Transition>
            </Menu>
          </div>
        </div>
      </div>
    </header>
  )
}