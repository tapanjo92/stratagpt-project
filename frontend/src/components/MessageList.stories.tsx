import type { Meta, StoryObj } from '@storybook/react'
import MessageList from './MessageList'
import { ChatMessage } from '@/types/chat'

const meta = {
  title: 'Components/MessageList',
  component: MessageList,
  parameters: {
    layout: 'centered',
  },
  decorators: [
    (Story) => (
      <div style={{ width: '600px', padding: '20px' }}>
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof MessageList>

export default meta
type Story = StoryObj<typeof meta>

const sampleMessages: ChatMessage[] = [
  {
    id: '1',
    role: 'user',
    content: 'What is the quorum for an AGM?',
    timestamp: new Date().toISOString(),
  },
  {
    id: '2',
    role: 'assistant',
    content: `Based on the strata by-laws, the quorum for an Annual General Meeting (AGM) is:

- **For small schemes (less than 20 lots)**: At least 50% of the unit entitlements must be represented
- **For large schemes (20+ lots)**: At least 25% of the unit entitlements must be represented

The quorum can be met through:
1. Physical attendance
2. Valid proxies
3. Pre-meeting voting (if permitted)

If quorum is not achieved within 30 minutes of the scheduled start time, the meeting must be adjourned.`,
    timestamp: new Date().toISOString(),
    citations: [
      {
        document_id: 'doc1',
        title: 'Model By-Laws',
        excerpt: 'Quorum requirements for AGM...',
      },
    ],
  },
  {
    id: '3',
    role: 'user',
    content: 'What happens if quorum is not met?',
    timestamp: new Date().toISOString(),
  },
  {
    id: '4',
    role: 'assistant',
    content: `If quorum is not met at an AGM, the following procedures apply:

1. **Wait 30 minutes**: The meeting must wait at least 30 minutes from the scheduled start time
2. **Adjourn the meeting**: If quorum is still not met, the meeting must be adjourned
3. **Reschedule**: A new meeting date must be set, typically within 7-14 days
4. **Reduced quorum**: At the adjourned meeting, those present constitute a quorum

This ensures important strata business can still be conducted even with lower attendance.`,
    timestamp: new Date().toISOString(),
  },
]

export const Default: Story = {
  args: {
    messages: sampleMessages,
  },
}

export const Empty: Story = {
  args: {
    messages: [],
  },
}

export const WithError: Story = {
  args: {
    messages: [
      ...sampleMessages.slice(0, 2),
      {
        id: '3',
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true,
      },
    ],
  },
}

export const LongConversation: Story = {
  args: {
    messages: [
      ...sampleMessages,
      {
        id: '5',
        role: 'user',
        content: 'Can the committee make decisions via email?',
        timestamp: new Date().toISOString(),
      },
      {
        id: '6',
        role: 'assistant',
        content: `Yes, committees can make decisions via email in most Australian states, subject to certain conditions:

**Requirements:**
- All committee members must have access to email
- The decision must be clearly proposed
- A reasonable time frame for responses must be given
- All members must respond (silence is not consent)

**Best Practices:**
1. Use a clear subject line indicating a decision is required
2. Set a specific deadline for responses
3. Document the decision in the next meeting minutes
4. Keep email records for audit purposes

**Limitations:**
- Cannot be used for decisions requiring a special resolution
- Some states require unanimous agreement for email decisions
- Complex matters are better discussed in meetings`,
        timestamp: new Date().toISOString(),
        citations: [
          {
            document_id: 'doc2',
            title: 'Committee Procedures',
            excerpt: 'Electronic voting procedures...',
          },
        ],
      },
    ],
  },
}