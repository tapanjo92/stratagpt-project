import type { Meta, StoryObj } from '@storybook/react'
import FileUpload from './FileUpload'

const meta = {
  title: 'Components/FileUpload',
  component: FileUpload,
  parameters: {
    layout: 'centered',
  },
  argTypes: {
    onUpload: { action: 'uploaded' },
  },
} satisfies Meta<typeof FileUpload>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  args: {
    accept: '.pdf,.docx,.txt',
    maxSize: 10,
  },
}

export const PDFOnly: Story = {
  args: {
    accept: '.pdf',
    maxSize: 5,
  },
}

export const LargeFileLimit: Story = {
  args: {
    accept: '.pdf,.docx,.txt',
    maxSize: 50,
  },
}